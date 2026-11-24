"""Equipment wiring reference and honest last-result communication indicators."""
from html import escape
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor,QFont,QPainter,QPainterPath,QPen,QPolygonF
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QDialog,QLabel,QGraphicsScene,QGraphicsView,
    QGraphicsPathItem,QGraphicsTextItem,QGraphicsEllipseItem,QGraphicsSimpleTextItem,QFrame)


class DiagramView(QGraphicsView):
    def __init__(self,scene):
        super().__init__(scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setBackgroundBrush(QColor('#ffffff'))
        self.setMinimumHeight(200)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        self.fitInView(self.sceneRect(),Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self,event):
        factor=1.15 if event.angleDelta().y()>0 else 1/1.15
        self.scale(factor,factor);event.accept()


class HelpPanel(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.config=None
        self.nodes={}
        layout=QVBoxLayout(self)
        title=QLabel('Help · schemat stanowiska i ostatni wynik komunikacji')
        title.setStyleSheet('font-weight:bold; font-size:15px;')
        layout.addWidget(title)
        self.banner=QLabel('Kontrolki nie są ciągłym monitoringiem. Zielony: poprawna odpowiedź; czerwony: błąd; szary: brak potwierdzenia.')
        self.banner.setWordWrap(True);layout.addWidget(self.banner)
        self.scene=QGraphicsScene(self)
        self.scene.setSceneRect(0,-25,1010,590)
        self.view=DiagramView(self.scene);layout.addWidget(self.view,1)
        tools=QHBoxLayout()
        expand=QPushButton('Otwórz duży schemat')
        expand.clicked.connect(self.expand_diagram);tools.addWidget(expand)
        self.diagram_zoom_in=QPushButton('+');self.diagram_zoom_in.clicked.connect(lambda:self.view.scale(1.25,1.25))
        tools.addWidget(self.diagram_zoom_in)
        self.diagram_zoom_out=QPushButton('−');self.diagram_zoom_out.clicked.connect(lambda:self.view.scale(.8,.8))
        tools.addWidget(self.diagram_zoom_out)
        fit=QPushButton('Autoscale');fit.clicked.connect(lambda:self.view.fitInView(self.scene.sceneRect(),Qt.AspectRatioMode.KeepAspectRatio))
        tools.addWidget(fit);tools.addStretch();layout.addLayout(tools)
        self.instructions=QLabel('1. Wybierz środowisko.  2. Ustaw adresy i kanały.  3. Wykonaj testy w konsoli. '
            '4. Sprawdź przebiegi, czasy i polaryzację.  5. Uruchom krótki pomiar.\n'
            'Zielona kontrolka nie potwierdza mocy RF, obecności światła ani kalibracji. '
            'Laser: ON=LOW zgodnie ze starym kodem. Dokładny kontroler lasera nie jest ustalony.')
        self.instructions.setWordWrap(True);layout.addWidget(self.instructions)
        from nv_lab.core.odmr import StationConfig
        self.set_station_config(StationConfig(),simulated=True)

    def expand_diagram(self):
        dialog=QDialog(self);dialog.setWindowTitle('NV Lab · schemat połączeń i kontrolki')
        dialog.resize(1150,800)
        layout=QVBoxLayout(dialog)
        note=QLabel('Kontrolki: ostatni wynik komunikacji. SIM oznacza symulator. '
                    'Kółko myszy przybliża, przeciąganie przesuwa schemat.')
        note.setWordWrap(True);layout.addWidget(note)
        view=DiagramView(self.scene);layout.addWidget(view,1)
        close=QPushButton('Zamknij');close.clicked.connect(dialog.accept);layout.addWidget(close)
        dialog.exec()
        dialog.deleteLater()

    def _box(self,key,title,body,x,y,width=240,height=105):
        path=QPainterPath();path.addRoundedRect(x,y,width,height,9,9)
        item=QGraphicsPathItem(path);item.setBrush(QColor('#eef4fc'));item.setPen(QPen(QColor('#bacce5'),1.5))
        self.scene.addItem(item)
        text=QGraphicsTextItem();text.setTextWidth(width-35)
        text.setHtml(f'<b>{escape(title)}</b><br><span style="font-size:11px">{escape(body).replace(chr(10),"<br>")}</span>')
        text.setDefaultTextColor(QColor('#17253d'));text.setFont(QFont('Segoe UI',11))
        text.setPos(x+8,y+3);self.scene.addItem(text)
        dot=QGraphicsEllipseItem(x+width-24,y+12,12,12)
        dot.setPen(QPen(Qt.PenStyle.NoPen));self.scene.addItem(dot)
        status=QGraphicsSimpleTextItem();status.setFont(QFont('Segoe UI',9));status.setPos(x+12,y+height-23)
        self.scene.addItem(status)
        self.nodes[key]=(dot,status,item)
        self._status(key,'unknown','Brak testu')

    def _arrow(self,points,label,color='#7286a5',label_at=None):
        path=QPainterPath(QPointF(*points[0]))
        for point in points[1:]:path.lineTo(*point)
        item=QGraphicsPathItem(path);item.setPen(QPen(QColor(color),2));self.scene.addItem(item)
        a,b=points[-2:]
        dx,dy=b[0]-a[0],b[1]-a[1];length=max(1,(dx*dx+dy*dy)**.5)
        ux,uy=dx/length,dy/length
        head=QPolygonF([QPointF(*b),QPointF(b[0]-9*ux+4*uy,b[1]-9*uy-4*ux),
                       QPointF(b[0]-9*ux-4*uy,b[1]-9*uy+4*ux)])
        self.scene.addPolygon(head,QPen(QColor(color)),QColor(color))
        text=self.scene.addText(label,QFont('Segoe UI',9));text.setDefaultTextColor(QColor(color))
        text.setPos(*(label_at or points[0]))

    def set_station_config(self,config,simulated):
        self.config=config;self.scene.clear();self.nodes={}
        self.banner.setStyleSheet('')
        self._arrow([(230,65),(300,65)],'LAN',label_at=(245,40))
        self._arrow([(120,20),(120,-18),(810,-18),(810,20)],'VISA / LAN',label_at=(600,-18))
        self._arrow([(20,65),(7,65),(7,540),(820,540),(820,505)],'USB / VISA',label_at=(680,540))
        self._arrow([(340,125),(340,175),(150,175),(150,225)],f'D{config.laser_channel} · laser TTL',label_at=(150,150))
        self._arrow([(550,85),(635,85),(635,185),(755,185),(755,225)],
            f'D{config.mw_channel} / A0(I), A1(Q)',label_at=(640,155))
        self._arrow([(815,125),(815,225)],'RF',label_at=(825,170))
        self._arrow([(550,110),(580,110),(580,140),(987,140),(987,370),(830,370),(830,400)],
            f'D{config.trigger_channel} → CH{config.scope_trigger_channel} trigger',label_at=(780,345))
        self._arrow([(260,275),(385,275)],'światło','#229368',(280,245))
        self._arrow([(700,275),(595,275)],'MW','#2468d9',(615,245))
        self._arrow([(490,330),(490,400)],'fluorescencja','#229368',(495,350))
        self._arrow([(595,450),(700,450)],f'CH{config.scope_channel}',label_at=(625,420))
        self._box('pc','PC · NV Lab','GUI, sekwencje, zapis danych',20,20,210)
        self._box('pulse_streamer','Pulse Streamer 8/2',
            f'D{config.trigger_channel}: TRIG · D{config.mw_channel}: MW\nD{config.laser_channel}: laser · A0/I, A1/Q',300,20,250)
        self._box('sg386','SRS SG386','Generator mikrofal · VISA',690,20,260)
        self._box('laser','Laser + modulator',f'Bramka TTL: ON={int(config.laser_active_high)}\nBrak odczytu mocy / prądu',40,225,220)
        self._box('nv','Próbka diamentu NV','Światło + mikrofale → odczyt PL',385,225,210)
        self._box('mw','Tor MW / bramka',f'Połączenia D{config.mw_channel} i I/Q\nwedług rzeczywistego okablowania',700,225,250)
        self._box('hmp4040','Zasilacz HMP4040','Poza bieżącą pętlą pomiarową',40,400,220)
        self._box('detector','Fotodetektor','Wyjście analogowe → oscyloskop',385,400,210)
        self._box('scope','DSO-X3034 · MY53160630',f'CH{config.scope_channel}: sygnał · CH{config.scope_trigger_channel}: trigger',700,400,250)
        self._status('pc','ok','Aplikacja działa')
        for key in ('nv','mw','detector'):self._status(key,'unknown','Tor fizyczny · do sprawdzenia')
        self._status('laser','unknown','Brak telemetrii')
        if simulated:
            self.banner.setText('SYMULATOR · Zielone kontrolki z dopiskiem SIM dotyczą urządzeń wirtualnych. Sprzęt fizyczny nie jest testowany.')
        else:
            self.banner.setText('SPRZĘT · Zielony: ostatnia odpowiedź OK; czerwony: błąd; szary: brak potwierdzenia. Brak ciągłego monitoringu.')

    def _status(self,key,state,message):
        if key not in self.nodes:return
        dot,text,item=self.nodes[key]
        color={'ok':'#158451','error':'#c13e49','pending':'#d09b20','unknown':'#8b98ac'}[state]
        dot.setBrush(QColor(color));text.setText(message);text.setBrush(QColor(color));item.setToolTip(message)

    def diagnostic(self,device,message,simulated=False):
        key='scope' if device in ('scope','scope-scale') else device
        if 'OK' in message:
            self._status(key,'ok','SIM · test OK' if simulated else 'OK · sesja zamknięta')
        elif any(value in message.lower() for value in ('nieudany','błąd','przerwano')):
            self._status(key,'error','SIM · błąd' if simulated else 'BŁĄD komunikacji')
        else:self._status(key,'pending','Test w toku…')

    def identities(self,identities,simulated,closed=False):
        for key in ('sg386','pulse_streamer','scope','hmp4040'):
            if key in identities:
                self._status(key,'ok','SIM · odpowiedź OK' if simulated else
                             'OK · sesja zamknięta' if closed else 'OK · identyfikacja')
        if simulated and 'laser' in identities:self._status('laser','ok','SIM · bramka TTL')

    def run_result(self,result):
        self.identities(result.identities,result.simulated,closed=True)
        if result.error or result.cleanup_errors:
            self.banner.setText(f'{"SIM" if result.simulated else "SPRZĘT"} · {result.state}: '
                f'{result.error or "; ".join(result.cleanup_errors)}. Szczegóły w konsoli.')
            self.banner.setStyleSheet('color:#b13443;')
            error=(result.error or '').lower()
            if any(word in error for word in ('oscyloskop','przebiegu','trigger','uśrednian','dso-x')):
                self._status('scope','error','BŁĄD ostatniej akwizycji')
            elif 'sg386' in error:self._status('sg386','error','BŁĄD komunikacji')
            elif 'pulse' in error:self._status('pulse_streamer','error','BŁĄD komunikacji')
            elif result.error:
                for key in ('sg386','pulse_streamer','scope'):
                    if key not in result.identities:
                        self._status(key,'error','BŁĄD otwierania sesji');break
        else:
            self.banner.setStyleSheet('')

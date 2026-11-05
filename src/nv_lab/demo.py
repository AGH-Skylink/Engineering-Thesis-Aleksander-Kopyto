from nv_lab.core.sequences import T1Settings, compile_t1

def main():
    params = T1Settings()
    for with_pi in (False, True):
        seq = compile_t1(params, with_pi=with_pi)
        print(f"T1 {'π' if with_pi else 'reference'} | duration={seq.duration_ns} ns")
        for name, pattern in seq.channels.items():
            print(f'  {name}: {pattern}')
    print('OFFLINE illustrative timeline only; no instruments contacted.')

if __name__ == '__main__':
    main()

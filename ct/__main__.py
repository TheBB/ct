from ct.scramble import CubeScrambler, CubeMove


def main():
    scrambler = CubeScrambler(5)
    for s in scrambler.scrambles():
        print(s)
        break


if __name__ == '__main__':
    main()

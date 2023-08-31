import multiprocessing
import sys


def test():
    print("hello from the other side")


def mp_test():
    print(sys.path)
    p = multiprocessing.Process(target=test)
    p.start()
    p.join()


if __name__ == '__main__':
    mp_test()

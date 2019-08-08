def uy_ci_verif(ci):
    verif, *ci_num = map(int, filter(lambda x: 47 < ord(x) < 58, reversed(ci)))
    # XXX maybe we should support other lenghts
    if 6 > len(ci_num) or len(ci_num) > 7:
        raise ValueError("wrong lenght")
    # TODO replace magic by function
    magic = (4, 3, 6, 7, 8, 9, 2)
    return verif == -sum((x * y for x, y in zip(magic, ci_num))) % 10

def uy_rut_verif(rut):
    verif, _, _, _, *rut_num = map(int, filter(lambda x: 47 < ord(x) < 58, reversed(rut)))
    if len(rut_num) != 8:
        raise ValueError("wrong lenght")
    def magic():
        while True:
            for i in range(2, 10):
                yield i
    return verif == -sum((x * y for x, y in zip(magic(), rut_num))) % 11

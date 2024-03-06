import struct
import dns
from dns import resolver


class DNSHeader:
    Struct = struct.Struct('!6H')

    def __init__(self):
        self.__dict__ = {
            field: None
            for field in
            ('ID', 'QR', 'OpCode', 'AA', 'TC', 'RD', 'RA', 'Z', 'RCode', 'QDCount', 'ANCount', 'NSCount', 'ARCount')}

    def parse_header(self, data):
        self.ID, misc, self.QDCount, self.ANcount, self.NScount, self.ARcount = DNSHeader.Struct.unpack_from(data)
        self.QR = (misc & 0x8000) != 0
        self.OpCode = (misc & 0x7800) >> 11
        self.AA = (misc & 0x0400) != 0
        self.TC = (misc & 0x200) != 0
        self.RD = (misc & 0x100) != 0
        self.RA = (misc & 0x80) != 0
        self.Z = (misc & 0x70) >> 4  # Never used
        self.RCode = misc & 0xF

    def __str__(self):
        return '<DNSHeader {}>'.format(str(self.__dict__))


def DNSquery(dn, stype):
    ans = resolver.resolve(dn, stype)
    print('Queries:')
    que = ans.response.question[0].to_text().split(' ')
    print(f'{que[0][:-1]}: type {que[2]}, class {que[1]}')
    print('Answers:')
    for a in ans.response.answer:
        tmp = a.to_text().split('\n')
        for t in tmp:
            tt = t.split(' ')
            print(f'{tt[0][:-1]}: type {tt[3]}, class {tt[2]}, TTL {tt[1]}, {tt[3]} {tt[4]}')
    if len(ans.response.authority) > 0:
        print('Authority:')
        tmp = ans.response.authority[0].to_text().split('\n')
        for t in tmp:
            tt = t.split(' ')
            print(f'{tt[0][:-1]}: type {tt[3]}, class {tt[2]}, TTL {tt[1]}, {tt[3]} {tt[4]}')


if __name__ == '__main__':
    DNSquery('www.bilibili.com', 'AAAA')
    # DNSquery('bilicdn1.com', 'NS')
    # DNSquery('163.com', 'MX')

from util import nios2_as, get_debug, require_symbols, hotpatch, get_regs
from csim import Nios2
import html
import collections


def check_jtag(asm, tests):
    obj = nios2_as(asm.encode('utf-8'))
    cpu = Nios2(obj=obj)

    class uart(object):
        def __init__(self):
            self.rx_fifo = collections.deque()
            self.tx_fifo = collections.deque()
            self.recvd = ''
            self.extra_info = ''

        def send_data(self, data):
            self.rx_fifo += [ord(x) for x in data]

        def drain_tx_fifo(self, n=-1):
            while (n == -1 or n > 0) and len(self.tx_fifo) > 0:
                if n > 0:
                    n -= 1
                self.recvd += chr(self.tx_fifo.popleft())

        def pop_data(self):
            self.drain_tx_fifo()
            r = self.recvd
            self.recvd = ''
            return r

        def pop_line(self):
            self.drain_tx_fifo()
            parts = self.recvd.split('\n', 1)
            if len(parts) != 2:
                return self.recvd
            r, self.recvd = parts
            return r + '\n'


        def uart_data(self, val=None):
            if val is not None:
                # stwio
                chr_data = val & 0xff
                if len(self.tx_fifo) >= 64:
                    # Lost the data!
                    self.extra_info += 'Warning: Wrote character \'%s\' (0x%02x) while transmit FIFO full!\n<br/>' %\
                        (html.escape(chr(chr_data)), chr_data)

                    self.extra_info += 'tx_fifo: %s <code>%s</code>\n<br/>' % \
                        (list(self.tx_fifo), html.escape(''.join([chr(c) for c in self.tx_fifo])))
                    self.extra_info += 'rx_fifo: %s <code>%s</code>\n<br/><br/>' % \
                        (list(self.rx_fifo), html.escape(''.join([chr(c) for c in self.rx_fifo])))

                    return

                self.tx_fifo.append(chr_data)

            else:
                # ldwio
                if len(self.rx_fifo) == 0:
                    return (len(self.rx_fifo) << 16) | (0x0<<15) | 0x41

                # Get next chr
                chr_data = self.rx_fifo.popleft()
                return (len(self.rx_fifo) << 16) | (0x1<<15) | chr_data

        def uart_ctrl(self, val=None):
            if val is None:
                # ldwio
                return (64 - len(self.tx_fifo)) << 16

        def ignore(self, val=None):
            return 0

        def nop(self):
            if True:
                err = cpu.get_error()
                self.feedback += 'Failed test case %d\n<br/>' % test_no
                self.feedback += 'Name: <code>%s</code><br/>' % html.escape(self.name)
                self.feedback += 'Got back <code>%s</code> %s<br/>' % (html.escape(self.recvd), self.recvd.encode('utf8').hex())
                #self.feedback += 'Got back <code>%s</code> %s<br/>' % (html.escape(self.recvd), self.recvd.hex())
                #self.recvd.encode('ascii').hex())

                self.feedback += get_debug(cpu)
                self.feedback += get_regs(cpu)
                self.feedback += 'tx_fifo: %s <code>%s</code>\n<br/>' % \
                        (list(self.tx_fifo), html.escape(''.join([chr(c) for c in self.tx_fifo])))
                self.feedback += 'rx_fifo: %s <code>%s</code>\n<br/>' % \
                        (list(self.rx_fifo), html.escape(''.join([chr(c) for c in self.rx_fifo])))
                return (False, err + self.feedback, self.extra_info)





    #tests = [[3, 5],
    #         [12, 8],
    #         [543, 222, 987]]
    extra_info = ''
    feedback = ''

    class HaltedCPU(Exception):
        def __init__(self, m):
            self.message = m
            super().__init__(self.message)

    def filtered_error(cpu):
        err = cpu.get_error()
        lines = [l for l in err.splitlines() if 'Instruction limit reached' not in l]
        return '\n'.join(lines)

    def run_a_bit(cpu, n_instrs=1000):
        #for i in range(n_instrs):
        #    cpu.one_step()
        n = cpu.run_until_halted(n_instrs)
        if n < n_instrs:
            raise HaltedCPU('CPU halted, only ran %d instructions (%s)' % (n, cpu.get_error()))
        cpu.unhalt()

    def encode(s):
        return '%s %s' % (ascii(s), ''.join([f"{ord(c):02x}" for c in s]))

    class InvalidRecv(Exception):
        def __init__(self, s, log, prefix="Error: Unexpected result"):
            self.s = s
            self.message = prefix + ' got %s' % encode(s) + '\n\nFull transcript:\n%s' % encode(log)
            super().__init__(self.message) # Call the base class constructor


    passed = True
    tot_ins = 0
    err = ''
    log = ''
    try:
        for i,tc in enumerate(tests):
            u = uart()
            cpu.reset()
            cpu.add_mmio(0xFF200000, u.ignore)
            cpu.add_mmio(0xFF201000, u.uart_data)
            cpu.add_mmio(0xFF201004, u.uart_ctrl)

            total = 0
            for n in tc:
                run_a_bit(cpu)
                #tot_ins += cpu.run_until_halted(5000)

                s = u.pop_data()
                log += s
                if s != 'Enter number:':
                    raise InvalidRecv(s, log, 'Error: did not get correct prompt.')

                # send in number
                u.send_data('%d' % n)

                run_a_bit(cpu)


                # check that we get our number echoed back
                s = u.pop_data()
                log += s
                if s != ('%d' % n):
                    raise InvalidRecv(s, log, 'Error: not echoing back entered number. Entered %d,' % n)

                # send in \n
                u.send_data('\n')

                # update our running total
                total += n

                run_a_bit(cpu)

                # Read our empty line
                s = u.pop_line()
                log += s
                if s != '\n':
                    raise InvalidRecv(s, log, 'Error: did not get back linebreak,')

                # Read total
                s = u.pop_line()
                log += s 
                if s != 'Total:%d\n' % total:
                    raise InvalidRecv(s, log, 'Error: recvd:%s did not get back correct total,' % encode(u.recvd))


    except InvalidRecv as e: 
        err = e.message
        passed = False
    except HaltedCPU as e:
        err = e.message
        passed = False

    if passed:
        return (True, err, u.extra_info)

    return (False, err, u.extra_info + filtered_error(cpu) + get_debug(cpu, mem_len=0x200, show_error=False))


import sys
tests = [[int(x) for x in sys.argv[1].split(',')]]
passed, err, info = check_jtag(sys.stdin.read(), tests)

if passed:
    print('Passed')
else:
    print('Failed on test %s' % sys.argv[1])
    print(err, info)
    

.text
.global _start
_start:
    movia   r2, 0xff200020  # Seven-segment MMIO
    movia   r3, 0xff200040  # Switches MMIO
    movia   r4, NUMS        # base address of digits array

    ######
    # Example code to display a digit (6) on the seven-segment display
    ######
    ldb     r5, 6(r4)       # read byte from NUMS[6]
    stwio   r5, 0(r2)       # write to 7-seg display

    break
.data
NUMS:
    .byte   0b00111111  # 0
    .byte   0b00000110  # 1
    .byte   0b01011011  # 2
    .byte   0b01001111  # 3
    .byte   0b01100110  # 4
    .byte   0b01101101  # 5
    .byte   0b01111101  # 6
    .byte   0b00000111  # 7
    .byte   0b01111111  # 8
    .byte   0b01100111  # 9

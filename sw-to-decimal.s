.text
.global _start

_start:
    movia   r2, 0xff200020  # Seven-segment MMIO
    movia   r3, 0xff200040  # Switches MMIO
    movia   r4, NUMS        # base address of digits array
    
	
binary_to_decimal:
	ldwio    r6, 0(r3)           # r6 stores the value of the switches
    mov     r10, r6             # copy of r6
	
	# one's place
    movi    r11, 10 			# divisor
    div     r7, r10, r11 		# compute the quotient by dividing by 10
    mul     r8, r7, r11			
    sub     r9, r10, r8         # subtract r9 from r10 and store this as remainder digit
	
	
	# store this into 7 segment MMIO
	add r12, r9, r4 			# this maps the decimal value we extracted to its
								# appropriate 7 segment MMIO
	ldb r13, 0(r12) 			# load this into the 7 segment MMIO
	
	# ten's place
	mov r10, r7 				# set r10 to the quotient
	div r7, r10, r11			# compute new quotient by dividing by 10
	mul r8, r7, r11
	sub r9, r10, r8
	
	# store this into 7 segment MMIO
	add r12, r9, r4 			# this maps the decimal value we extracted to its
								# appropriate 7 segment MMIO
	ldb r14, 0(r12) 			# load this into the 7 segment MMIO
	
	
	# hundreds 
	mov r10, r7
	div r7, r10, r11			
	mul r8, r7, r11
	sub r9, r10, r8
	
	add     r12, r4, r9
    ldb     r15, 0(r12)
	
	
	#thousands
	mov     r10, r7
	div     r7, r10, r11
	mul     r8, r7, r11
	sub     r9, r10, r8

	add     r12, r4, r9
	ldb     r16, 0(r12)
	
	
	# shift left to store numbers in the 7 segment display
	slli    r16, r16, 24
    slli    r15, r15, 16
    slli    r14, r14, 8

	# or operator allows us to combine all of the digits into one hex value
    or      r17, r16, r15
    or      r17, r17, r14
    or      r17, r17, r13

	# display
    stwio   r17, 0(r2)
	
	
	br binary_to_decimal
	

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

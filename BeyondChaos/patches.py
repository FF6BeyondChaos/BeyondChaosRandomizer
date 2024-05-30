from io import BytesIO
import os

from bcg_junction import (write_patch as jm_write_patch,
                          tblpath as jm_tblpath)
from randomtools.tablereader import verify_patches as rt_verify_patches
from character import get_characters
from utils import Substitution, RANDOM_MULTIPLIER, random

import math


def allergic_dog(output_rom_buffer: BytesIO):
    # auto-float doesn't remove Interceptor
    allergic_dog_sub = Substitution()
    allergic_dog_sub.set_location(0x391c4)
    allergic_dog_sub.bytestring = bytes([
        0x20, 0xF2, 0x93,  # JSR $93F2  		; Define Y
        0xAD, 0x32, 0x30,  # LDA $3032  		; Gear status immunity
        0x20, 0xEC, 0x91,  # JSR $91EC  		; Cure affected ailments
        0xAD, 0x34, 0x30,  # LDA $3034  		; Gear-granted status
        0x19, 0x15, 0x00,  # ORA $0015,Y		; Add actor status
        0x4A,              # LSR A      		; Auto Float or Rage?
        0x90, 0x15,        # BCC $15    		; Exit if not
        0xB9, 0x15, 0x00,  # LDA $0015,Y		; Actor status
        0x29, 0x40,        # AND #$40   		; Get Interceptor
        0x85, 0xE0,        # STA $E0    		; Memorize it
        0xAD, 0x34, 0x30,  # LDA $3034  		; Gear-granted status
        0x29, 0x01,        # AND #$01   		; Auto Float?
        0xF0, 0x02,        # BEQ $02    		; Skip next line if not
        0xA9, 0x81,        # LDA #$81   		; Enable Rage, Float
        0x05, 0xE0,        # ORA $E0    		; Add Interceptor back
        0x99, 0x15, 0x00,  # STA $0015,Y		; Set actor status
        0x60               # RTS
    ])
    allergic_dog_sub.write(output_rom_buffer)


# Moves check for dead banon after Life 3 so he doesn't revive and then game over.
def banon_life3(output_rom_buffer: BytesIO):
    banon_sub = Substitution()
    banon_sub.set_location(0x206bf)
    banon_sub.bytestring = [
        0x89, 0xC2,        # BIT #$C2       (Check for Dead, Zombie, or Petrify status)
        # 06C1
        0xF0, 0x09,        # BEQ $06CC      (branch if none set)
        # 06C3
        0xBD, 0x19, 0x30,  # LDA $3019,X
        # 06C6
        0x0C, 0x3A, 0x3A,  # TSB $3A3A      (add to bitfield of dead-ish or escaped monsters)
        # 06C9
        0x20, 0xC8, 0x07,  # JSR $07C8      (Clear Zinger, Love Token, and Charm bonds, and
                           #                 clear applicable Quick variables)
        # 06CC
        0xBD, 0xE4, 0x3E,  # LDA $3EE4,X
        # 06CF
        0x10, 0x2F,        # BPL $0700      (Branch if alive)
        # 06D1
        0x20, 0x10, 0x07,  # JSR $0710      (If Wound status set on mid-Jump entity, replace
                           #                 it with Air Anchor effect so they can land first)
        # 06D4
        0xBD, 0xE4, 0x3E,  # LDA $3EE4,X
        # 06D7
        0x89, 0x02,        # BIT #$02
        # 06D9
        0xF0, 0x03,        # BEQ $06DE      (branch if no Zombie Status)
        # 06DB
        0x20, 0x28, 0x07,  # JSR $0728      (clear Wound status, and some other bit)
        # 06DE
        0xBD, 0xE4, 0x3E,  # LDA $3EE4,X
        # 06E1
        0x10, 0x1D,        # BPL $0700      (Branch if alive)
        # 06E3
        0xBD, 0xF9, 0x3E,  # LDA $3EF9,X
        # 06E6
        0x89, 0x04,        # BIT #$04
        # 06E8
        0xF0, 0x05,        # BEQ $06EF      (branch if no Life 3 status)
        # 06EA
        0x20, 0x99, 0x07,  # JSR $0799      (prepare Life 3 revival)
        # 06ED
        0x80, 0x11,        # BRA $0700
        # 06EF
        0xE0, 0x08,        # CPX #$08
        # 06F1
        0xB0, 0x0C,        # BCS $06E4      (branch if monster)
        # 06F3
        0xBD, 0xD8, 0x3E,  # LDA $3ED8,X    (Which character)
        # 06F6
        0xC9, 0x0E,        # CMP #$0E
        # 06F8
        0xD0, 0x06,        # BNE $0700      (Branch if not Banon)
        # 06FA
        0xA9, 0x06,        # LDA #$06
        # 06FC
        0x8D, 0x6E, 0x3A,  # STA $3A6E      (Banon fell... "End of combat" method #6)
        # 06FF
        0xEA,
    ]
    banon_sub.write(output_rom_buffer)


def evade_mblock(output_rom_buffer: BytesIO):
    evade_mblock_sub = Substitution()
    evade_mblock_sub.bytestring = bytes([
        0xF0, 0x17, 0x20, 0x5A, 0x4B, 0xC9, 0x40, 0xB0, 0x9C, 0xB9, 0xFD, 0x3D,
        0x09, 0x04, 0x99, 0xFD, 0x3D, 0x80, 0x92, 0xB9, 0x55, 0x3B, 0x48,
        0x80, 0x43, 0xB9, 0x54, 0x3B, 0x48, 0xEA
    ])
    evade_mblock_sub.set_location(0x2232C)
    evade_mblock_sub.write(output_rom_buffer)


def fix_xzone(output_rom_buffer: BytesIO):
    fix_xzone_sub = Substitution()
    fix_xzone_sub.set_location(0x1064B7)  # force draw monsters struck by Life animation (includes reraise)
    fix_xzone_sub.bytestring = bytes([0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0xF1, 0x81, 0xFF])
    fix_xzone_sub.write(output_rom_buffer)

    fix_xzone_sub = Substitution()
    fix_xzone_sub.set_location(0x0235A3)                       # Hook point in Runic function
    fix_xzone_sub.bytestring = bytes([0x22, 0xD5, 0xB9, 0xC4,  # JSL $C4B9D5, go to subroutine
                                      0xEA])                   # NOP
    fix_xzone_sub.write(output_rom_buffer)

    fix_xzone_sub = Substitution()
    fix_xzone_sub.set_location(0x04B9D5)  # Subroutine hooked from Runic function, sets bit #$04 of $11A7 when a Runic catch has occurred
    fix_xzone_sub.bytestring = bytes([0xA9, 0x04,        # LDA #$04
                                      0x0C, 0xA7, 0x11,  # TSB $11A7, formerly unused bit on Monster Text attack byte, now "Don't hide character/monster" bit
                                      0xA9, 0x03,        # LDA #$03
                                      0x1C, 0xA7, 0x11,  # TRB $11A7, displaced code, turn off text if hits and miss if status isn't set]
                                      0x6B])             # RTL
    fix_xzone_sub.write(output_rom_buffer)

    fix_xzone_sub = Substitution()
    fix_xzone_sub.set_location(0x01E2EE)  # Hook point in Show/Hide Character/Monster animation command, monster branch
    fix_xzone_sub.bytestring = bytes([0x22, 0xE0, 0xB9, 0xC4,   # JSL $C4B9E0, go to subroutine
                                      0xEA, 0xEA, 0xEA, 0xEA])  # NOP x4
    fix_xzone_sub.write(output_rom_buffer)

    fix_xzone_sub = Substitution()
    fix_xzone_sub.set_location(0x04B9E0)  # Subroutine hooked from Show/Hide Character/Monster animation command, bypasses hide if bit #$04 of $11A7 is set
    fix_xzone_sub.bytestring = bytes([0xAD, 0xA7, 0x11,  # LDA $11A7
                                      0x89, 0x04,        # BIT #$04, is our new "Don't hide character/monster" bit set?
                                      0xD0, 0x08,        # BNE #$08, if so, don't hide monster
                                      0xAD, 0xAB, 0x61,  # LDA $61AB
                                      0x25, 0x10,        # AND $10
                                      0x8D, 0xAB, 0x61,  # STA $61AB
                                      0x6B])             # RTL
    fix_xzone_sub.write(output_rom_buffer)

    fix_xzone_sub = Substitution()
    fix_xzone_sub.set_location(0x01E31C)  # Hook point in Show/Hide Character/Monster animation command, character branch
    fix_xzone_sub.bytestring = bytes([0x22, 0xF0, 0xB9, 0xC4,   # JSL $C4B9F0, go to subroutine
                                      0xEA, 0xEA, 0xEA, 0xEA])  # NOP #4
    fix_xzone_sub.write(output_rom_buffer)

    fix_xzone_sub = Substitution()
    fix_xzone_sub.set_location(0x04B9F0)  # Subroutine hooked from Show/Hide Character/Monster animation command, bypasses hide if bit #$04 of $11A7 is set
    fix_xzone_sub.bytestring = bytes([0xAD, 0xA7, 0x11,  # LDA $11A7
                                      0x89, 0x04,        # BIT #$04, is our new "Don't hide character/monster" bit set?
                                      0xD0, 0x08,        # BNE #$08, if so, don't hide monster
                                      0xAD, 0xAC, 0x61,  # LDA $61AC
                                      0x25, 0x10,        # AND $10
                                      0x8D, 0xAC, 0x61,  # STA $61AC
                                      0x6B])             # RTL
    fix_xzone_sub.write(output_rom_buffer)


def imp_skimp(output_rom_buffer: BytesIO):
    imp_skimp_sub = Substitution()

    # imp_skimp_sub.set_location(0x011116)
    # imp_skimp_sub.bytestring = bytes([0x1A, 0xD7])
    # imp_skimp_sub.write(output_rom_buffer)

    imp_skimp_sub.set_location(0x012F7F)
    imp_skimp_sub.bytestring = bytes([0x4A, 0x6A, 0x6A, 0x6A, 0xAA, 0xBD, 0xCD, 0x61, 0xF0, 0x03, 0x4C, 0x1A, 0x30, 0x1A, 0x9D, 0xCE,
                                      0x61, 0x2D, 0x4B, 0x2F, 0xD0, 0x16, 0xBD, 0xC0, 0x2E, 0x29, 0x08, 0xF0, 0x04, 0xA9, 0x12, 0x80,
                                      0x0E, 0xBD, 0xBD, 0x2E, 0x29, 0x20, 0xF0, 0x04, 0xA9, 0x0F, 0x80, 0x03, 0xBD, 0xAE, 0x2E, 0xD9,
                                      0x6C, 0x7B, 0xF0, 0x0A, 0x99, 0x6C, 0x7B, 0x20, 0x57, 0x31, 0x7B, 0x99, 0x70, 0x7B, 0xAD, 0x4B,
                                      0x2F, 0x4A, 0xB0, 0x1E, 0xBD, 0xBD, 0x2E, 0x29, 0x10, 0xF0, 0x17, 0xB9, 0x70, 0x7B, 0xD0, 0x31,
                                      0xAD, 0x6A, 0x7B, 0xD0, 0x2C, 0xEE, 0x6A, 0x7B, 0x20, 0x50, 0x30, 0x20, 0x06, 0x31, 0xA9, 0x01,
                                      0x80, 0x17, 0xB9, 0x70, 0x7B, 0xF0, 0x1A, 0xAD, 0x6A, 0x7B, 0xD0, 0x15, 0xEE, 0x6A, 0x7B, 0x20,
                                      0x50, 0x30, 0xB9, 0x6C, 0x7B, 0x20, 0x57, 0x31, 0x7B, 0x99, 0x70, 0x7B, 0xA9, 0x1E, 0x9D, 0xCD,
                                      0x61, 0x9E, 0xCE, 0x61, 0x20, 0x71, 0x30, 0x20, 0x24, 0x2F, 0xC2, 0x20, 0xBD, 0xBD, 0x2E, 0x9D,
                                      0xC1, 0x2E, 0xBD, 0xBF, 0x2E, 0x9D, 0xC3, 0x2E, 0x7B, 0xE2, 0x20, 0xEE, 0x78, 0x7B, 0x60, 0xF4,
                                      0xC0, 0x25, 0x7B, 0xAA, 0xA8, 0x5E, 0xC2, 0x62, 0x90, 0x01, 0xC8, 0x1E, 0xC2, 0x62, 0xE8, 0xE0,
                                      0x06, 0x00, 0xD0, 0xF1, 0x98, 0xF0, 0x03, 0x4C, 0x7C, 0x25, 0x4C, 0x5D, 0x32, 0xBD, 0xEC, 0x3E,
                                      0x29, 0x20, 0x59, 0xC2, 0x62, 0x4A, 0xF0, 0x08, 0x0A, 0x59, 0xC2, 0x62, 0x1A, 0x99, 0xC2, 0x62])
    imp_skimp_sub.write(output_rom_buffer)

    imp_skimp_sub.set_location(0x013247)
    imp_skimp_sub.bytestring = bytes([0x69, 0x37, 0xCF, 0xAA, 0xA0, 0xC4, 0x64, 0xA9, 0x07, 0x00, 0x8B, 0x54, 0x7E, 0xC2, 0xAB, 0x7B,
                                      0xE2, 0x20, 0xEE, 0xBB, 0x64, 0x60, 0xFA, 0xE0, 0xC0, 0x25, 0xF0, 0x01, 0xDA, 0x60, 0x1A, 0x0C,
                                      0xC2, 0x62, 0x60])
    imp_skimp_sub.write(output_rom_buffer)

    imp_skimp_sub.set_location(0x0191D4)
    imp_skimp_sub.bytestring = bytes([0x20, 0x1B, 0xD7])
    imp_skimp_sub.write(output_rom_buffer)

    imp_skimp_sub.set_location(0x019369)
    imp_skimp_sub.bytestring = bytes([0x20, 0x1B, 0xD7])
    imp_skimp_sub.write(output_rom_buffer)

    imp_skimp_sub.set_location(0x0193C5)
    imp_skimp_sub.bytestring = bytes([0x20, 0x1B, 0xD7])
    imp_skimp_sub.write(output_rom_buffer)

    imp_skimp_sub.set_location(0x01C8AB)
    imp_skimp_sub.bytestring = bytes([0x3F, 0xD7, 0x2F, 0xD7, 0x3C])
    imp_skimp_sub.write(output_rom_buffer)

    imp_skimp_sub.set_location(0x01D6E8)
    imp_skimp_sub.bytestring = bytes([0x20, 0xF1, 0xD6, 0xCA, 0x20, 0xF1, 0xD6, 0xE8, 0x60, 0xBD, 0x39, 0x6A, 0xDA, 0x30, 0x17, 0x29,
                                      0x03, 0x8D, 0x78, 0x7B, 0x0A, 0xA8, 0x0A, 0x0A, 0x0A, 0x0A, 0xAA, 0xB9, 0xE4, 0x3E, 0x9D, 0xBD,
                                      0x2E, 0x20, 0x79, 0x2F, 0xFA, 0x60, 0x69, 0x7C, 0xA8, 0x0A, 0xAA, 0x20, 0x3C, 0x30, 0x20, 0x1E,
                                      0x30, 0xFA, 0x60, 0x7B, 0xAA, 0xA8, 0x20, 0x65, 0x32, 0x20, 0x3C, 0x30, 0xE8, 0xE8, 0xC8, 0xC0,
                                      0x06, 0x00, 0xD0, 0xF5, 0x4C, 0x21, 0x30, 0x20, 0x5B, 0x18, 0xAE, 0xF6, 0x7A, 0x9D, 0xD8, 0x74,
                                      0x9E, 0xD9, 0x74, 0x60, 0x7B, 0x80, 0xF3, 0xC2, 0x20, 0xAE, 0xF6, 0x7A, 0xBD, 0x82, 0x6F, 0x9D,
                                      0x3A, 0x6A, 0xBD, 0x84, 0x6F, 0x9D, 0x3C, 0x6A, 0x80, 0x23])
    imp_skimp_sub.write(output_rom_buffer)

    imp_skimp_sub.set_location(0x101F51)  # Green Cherry Animation
    imp_skimp_sub.bytestring = bytes([0xFA, 0x7A, 0x1F, 0xFF, 0xFF])
    imp_skimp_sub.write(output_rom_buffer)

    imp_skimp_sub.set_location(0x101F6C)  # Remedy Animation
    imp_skimp_sub.bytestring = bytes([0x8C, 0x1F, 0xBF, 0x8C, 0x1F, 0xBF, 0x8C, 0x1F, 0xBF, 0x8C, 0x1F, 0x80, 0x13, 0xFF, 0x8B, 0x07,
                                      0x00, 0x8C, 0x80, 0x13, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
                                      0xE9, 0x1F, 0x00, 0x8B, 0x03, 0x80, 0x65, 0x00, 0x80, 0x65, 0x00, 0x8C, 0x89, 0x09, 0x83, 0xCF,
                                      0x80, 0x65, 0x03, 0x80, 0x65, 0x03, 0x8A, 0x89, 0x04, 0x83, 0x3F, 0x8A])
    imp_skimp_sub.write(output_rom_buffer)

    imp_skimp_sub.set_location(0x103433)  # Rippler Animation
    imp_skimp_sub.bytestring = bytes([0xFA, 0x0D, 0x5F])
    imp_skimp_sub.write(output_rom_buffer)

    imp_skimp_sub.set_location(0x105F02)  # Imp Animation
    imp_skimp_sub.bytestring = bytes([0x13, 0x89, 0x2C, 0xA6, 0x00, 0x00, 0xFF, 0xA7, 0x00, 0x8A, 0xFF, 0xAD, 0x03, 0x80, 0x13, 0xFF,
                                      0xD1, 0x00, 0x80, 0x13, 0xFF, 0xFF, 0xFF])
    imp_skimp_sub.write(output_rom_buffer)

    imp_skimp_sub.set_location(0x10790C)  # Bio Blaster Animation
    imp_skimp_sub.bytestring = bytes([0xFA, 0x12, 0x5F])
    imp_skimp_sub.write(output_rom_buffer)


def death_abuse(output_rom_buffer: BytesIO):
    death_abuse_sub = Substitution()
    death_abuse_sub.bytestring = bytes([0x60])
    death_abuse_sub.set_location(0xC515)
    death_abuse_sub.write(output_rom_buffer)


def no_kutan_skip(output_rom_buffer: BytesIO):
    no_kutan_skip_sub = Substitution()
    no_kutan_skip_sub.set_location(0xAEBC2)
    no_kutan_skip_sub.bytestring = bytes([0x27, 0x01])
    no_kutan_skip_sub.write(output_rom_buffer)

def mastered_espers(output_rom_buffer: BytesIO, dancingmaduin=False):

    me_sub = Substitution()

    #Turn empty small font icon $7F into a star
    me_sub.set_location(0x487B0)
    me_sub.bytestring = bytes([0x18, 0x00, 0x3C, 0x18, 0xFF, 0x18, 0xFF, 0x7E, 0x7E,
                               0x3C, 0xFF, 0x7E, 0xFF, 0x66, 0xE7, 0x00])
    me_sub.write(output_rom_buffer)

    #Hook into the Skills menu initiation to run a subroutine in freespace
    me_sub.set_location(0x31B61)
    me_sub.bytestring = bytes([0x20, 0xB0, 0xFE]) #Hook - calculate actor's spell starting RAM offset; # JSL $EEB0A6, Set up Yellow font and Calculate actor's spell offset, 0xD2 bytes after start of code block
    me_sub.write(output_rom_buffer)

    me_sub.set_location(0x3FEB0)
    if dancingmaduin:
         me_sub.bytestring = bytes([ 0x22, 0xA6, 0xB0, 0xEE, 0x20, 0x00, 0xF8, 0x60])
    else:
        me_sub.bytestring = bytes([0x22, 0xA6, 0xB0, 0xEE, 0x60])
    me_sub.write(output_rom_buffer)

    #Hook into "Draw Esper name and MP cost" function to run a check from freespace and draw the star
    me_sub.set_location(0x35509)
    me_sub.bytestring = bytes([0x22, 0xD4, 0xAF, 0xEE,					# JSL $EEAFD4, Draw Esper name and MP cost
		                        0x20, 0x9F, 0x80,						# JSR $809F, Compute string map pointer
		                        0xC2, 0x20,])							# REP #$20
    me_sub.write(output_rom_buffer)

    me_sub.set_location(0x3552E)
    me_sub.bytestring = bytes([0x22, 0x04, 0xB0, 0xEE])  #Hook - check if current esper is mastered; # JSL $EEB004, Check if mastered, 0x30 bytes after start of code block
    me_sub.write(output_rom_buffer)

    me_sub.set_location(0x35548)
    me_sub.bytestring = bytes([0x22, 0x51, 0xB0, 0xEE,					# Draw Digits, 0x7D bytes after start of code block
		                        0x20, 0xD9, 0x7F,						# JSR $7FD9, Draw string
		                        0x22, 0x64, 0xB0, 0xEE,					# JSL $EEB064, Add Star, 0x90 bytes after start of code block
		                        0x20, 0xD9, 0x7F,						# JSR $7FD9, Draw string
		                        0x60])  								# RTS  #Hook - add star Icon
    me_sub.write(output_rom_buffer)

    me_sub.set_location(0x3555D)
    me_sub.bytestring = bytes([0xA0, 0x0D, 0x00]) #Constant adjustment - Blank 13 tiles
    me_sub.write(output_rom_buffer)

    #Freespace after "Improved Party Gear" Patch
    me_sub.set_location(0x2EAFD4)
    me_sub.bytestring = bytes([0xC2, 0x20,							# REP #$20
                                0x8A,								# TXA
                                0x18,								# CLC
                                0x69, 0x0C, 0x00,					# ADC $000C
                                0x85, 0xF5,							# STA $F5, save icon position
                                0xE2, 0x20,							# SEP #$20
                                0xA5, 0xE6,							# LDA $E6
                                0x1A,								# INC
                                0x6B,								# RTL

                                0x7B,								# TDC, in this context puts 0 into A register
                                0xA5, 0x28,							# LDA $28
                                0xAA,								# TAX
                                0xB5, 0x69,							# LDA $69,X
                                0xEB,								# XBA
                                0xA9, 0x36,							# LDA #$36
                                0xC2, 0x20,							# REP #$20, puts A into 16-bit mode
                                0x8F, 0x02, 0x42, 0x00,				# STA $004202, prepare for SNES hardware multiplication of A and B
                                0xEA, 0xEA, 0xEA, 0xEA,				# NOP #4, wait for it to finish
                                0xAF, 0x16, 0x42, 0x00,				# LDA $004216, get the result
                                0x8D, 0x03, 0x02,					# STA $0203
                                0xE2, 0x20,							# SEP #$20, back to A in 8-bit mode
                                0x7B,								# TDC
                                0xA5, 0x28,							# LDA $28
                                0xAA,								# TAX
                                0x6B,								# RTL, end of routine "Calculate Actor's spell starting RAM offset"

                                0xDA,								# PHX
                                0x5A,								# PHY
                                0x7B,								# TDC
                                0x85, 0xFB,							# STA $FB, clear the Mastered Esper byte
                                0xBF, 0x89, 0x9D, 0x7E,				# LDA $7E9D89, load Esper ID
                                0xC2, 0x20,							# REP #$20, puts A into 16-bit mode
                                0x85, 0xFC,							# STA $FC
                                0x0A,								# ASL
                                0x85, 0xFE,							# STA $FE
                                0x0A, 0x0A,							# ASL #2
                                0x18,								# CLC
                                0x65, 0xFE,							# ADC $FE
                                0x18,								# CLC
                                0x65, 0xFC,							# ADC $FC, now eleven times the Esper ID
                                0xAA,								# TAX
                                0x64, 0xFC,							# STZ $FC
                                0xA0, 0x05, 0x00,					# LDY #$0005, Five spells max per Esper
                                0xE2, 0x20,							# SEP #$20, back to 8-Bit A
                                0x7B,								# TDC, Clear A.  [This is the start of the loop]
                                0xBF, 0x01, 0x6E, 0xD8,				# LDA $D86E01,X, Esper Spell
                                0xC9, 0xFF,							# CMP #$FF, is it empty?
                                0xF0, 0x1B,							# BEQ $1B, branch if so
                                0x85, 0xFC,							# STA $FC
                                0xC2, 0x20,							# REP #$20, back to 16-Bit A
                                0xAD, 0x03, 0x02,					# LDA $0203, current character spell offset
                                0x18,								# CLC
                                0x65, 0xFC,							# ADC $FC, Spell Offset + Spell ID
                                0xDA,								# PHX, save Esper data index
                                0xAA,								# TAX, set X as spell learnt percentage
                                0xE2, 0x20,							# SEP #$20, back to 8-Bit A
                                0xBD, 0x6E, 0x1A,					# LDA $1A6E,X, spell learnt percentage
                                0xFA,								# PLX, restore Esper data index
                                0xC9, 0xFF,							# CMP #$FF, is the spell learned?
                                0xD0, 0x07,							# BNE $07, Branch if not, out of loop, to prevent marking the Esper as mastered
                                0xE8, 0xE8,							# INX #2
                                0x88,								# DEY
                                0xD0, 0xDC,							# BNE $DC, go back to the start of the loop if we haven't checked five spells
                                0xE6, 0xFB,							# INC $FB, mark Esper as mastered
                                0x7A,								# PLY
                                0xFA,								# PLX
                                0xBF, 0x89, 0x9D, 0x7E,				# LDA $7E8D89,X, load Esper ID
                                0x6B,								# RTL, end of routine "Check if current Esper is mastered"

                                0xA5, 0xF7,							# LDA $F7, hundreds digit
                                0x8D, 0x80, 0x21,					# STA $2180, add to string
                                0xA5, 0xF8,							# LDA $F8, tens digit
                                0x8D, 0x80, 0x21,					# STA $2180, add to string
                                0xA5, 0xF9,							# LDA $F9, ones digit
                                0x8D, 0x80, 0x21,					# STA $2180, add to string
                                0x9C, 0x80, 0x21,					# STZ $2180, end string
                                0x6B,								# RTL, end of routine "Draw Digits"

                                0xA6, 0xF5,							# LDX $F5, Icon's X position
                                0xA5, 0xE6,							# LDA $E6, BG1 write row
                                0x1A,								# INC, go down one row
                                0xEB,								# XBA
                                0xA5, 0x00,							# LDA $00
                                0xEB,								# XBA
                                0xC2, 0x20,							# REP #$20, set 16-Bit A
                                0x0A, 0x0A, 0x0A, 0x0A, 0x0A, 0x0A,	# ASL #6, times sixty-four
                                0x85, 0xE7,							# STA $E7
                                0x8A,								# TXA
                                0x0A,								# ASL
                                0x18,								# CLC
                                0x65, 0xE7,							# ADC $E7
                                0x69, 0x49, 0x38,					# ADC #$3849
                                0x8F, 0x89, 0x9E, 0x7E,				# STA $7E9E89, set position
                                0xE2, 0x20,							# SEP #$20, set 8-Bit A
                                0xA5, 0x29,							# LDA $29, load font palette
                                0xC9, 0x20,							# CMP #$20, check if it's the active character palette
                                0xD0, 0x04,							# BNE $04, branch if it's grayed out
                                0xA9, 0x34,							# LDA #$34, set palette to yellow (using Myria's code)
                                0x85, 0x29,							# STA $29
                                0xA2, 0x8B, 0x9E,					# LDX #$9E8B
                                0x8E, 0x81, 0x21,					# STX $2181
                                0xA5, 0xFB,							# LDA $FB, mastered Esper byte
                                0xF0, 0x04,							# BEQ $04, branch if not mastered
                                0xA9, 0x7F,							# LDA #$7F, Esper star icon
                                0x80, 0x02,							# BRA $02
                                0xA9, 0xFF,							# LDA #$FF, empty glyph
                                0x8D, 0x80, 0x21,					# STA $2180, add to string
                                0x9C, 0x80, 0x21,					# STZ $2180, end string
                                0x6B,								# RTL, end of routine "Add Star"

                                0x22, 0x01, 0xAF, 0xEE,				# JSL Myria's Yellow Font code
                                0x22, 0xE3, 0xAF, 0xEE,				# JSL Calculate actor's spell offset, 0x0F bytes after start of code block
                                0x6B])								# RTL

    me_sub.write(output_rom_buffer)

    ## Next free byte is 0x2EB0AF

def show_coliseum_rewards(output_rom_buffer: BytesIO):
    rewards_sub = Substitution()
    rewards_sub.set_location(0x37FD0)
    rewards_sub.bytestring = bytes([
        0x4C, 0x00, 0xF9
    ])
    rewards_sub.write(output_rom_buffer)

    rewards_sub.set_location(0x3F900)
    rewards_sub.bytestring = bytes([
        0xA5, 0x26, 0xC9, 0x71, 0xF0, 0x0D, 0xC9, 0x72, 0xF0, 0x09, 0x20, 0xB9, 0x80,
        0x20, 0xD9, 0x7F, 0x4C, 0xE6, 0x7F, 0x20, 0x3B, 0xF9, 0x20, 0x49, 0xF9, 0x20,
        0xAB, 0xF9, 0x20, 0x50, 0xF9, 0x20, 0x66, 0xF9, 0x20, 0x49, 0xF9, 0x20, 0x97,
        0xF9, 0x20, 0x50, 0xF9, 0x20, 0x61, 0xF9, 0x20, 0x49, 0xF9, 0x20, 0x78, 0xF9,
        0x20, 0x50, 0xF9, 0x20, 0x66, 0xF9, 0x60, 0x7B, 0xA5, 0xE5, 0xA8, 0xB9, 0x69,
        0x18, 0x8D, 0x05, 0x02, 0x20, 0x2C, 0xB2, 0x60, 0xA2, 0x8B, 0x9E, 0x8E, 0x81,
        0x21, 0x60, 0x20, 0xD9, 0x7F, 0x60, 0xA2, 0x0D, 0x00, 0x8D, 0x80, 0x21, 0xCA,
        0xD0, 0xFA, 0x9C, 0x80, 0x21, 0x60, 0xA2, 0x02, 0x00, 0x80, 0x03, 0xA2, 0x1A,
        0x00, 0xC2, 0x20, 0x8A, 0x18, 0x6F, 0x89, 0x9E, 0x7E, 0x8F, 0x89, 0x9E, 0x7E,
        0xE2, 0x20, 0x60, 0xAD, 0x09, 0x02, 0xD0, 0x0E, 0xAD, 0x05, 0x02, 0xC9, 0xFF,
        0xF0, 0x0D, 0xAD, 0x07, 0x02, 0x20, 0x68, 0xC0, 0x60, 0xA9, 0xBF, 0x20, 0x54,
        0xF9, 0x60, 0xA9, 0xFF, 0x20, 0x54, 0xF9, 0x60, 0xAD, 0x05, 0x02, 0xC9, 0xFF,
        0xF0, 0x04, 0xA9, 0xC1, 0x80, 0x02, 0xA9, 0xFF, 0x8D, 0x80, 0x21, 0x9C, 0x80,
        0x21, 0x60, 0xAD, 0x05, 0x02, 0xC9, 0xFF, 0xF0, 0x07, 0xAD, 0x05, 0x02, 0x20,
        0x68, 0xC0, 0x60, 0xA9, 0xFF, 0x20, 0x54, 0xF9, 0x60, 0xFF
        ])
    rewards_sub.write(output_rom_buffer)


def sprint_shoes_break(output_rom_buffer: BytesIO):

    #Also make Rename Card item slot usable in battle

    sprint_shoes_sub = Substitution()
    sprint_shoes_sub.set_location(0x2273D)
    sprint_shoes_sub.bytestring = bytes([0xE8])
    sprint_shoes_sub.write(output_rom_buffer)


def cycle_statuses(output_rom_buffer: BytesIO):
    cycles_sub = Substitution()
    cycles_sub.set_location(0x012E4F)  # C12E4F
    cycles_sub.bytestring = bytes([0x80, 0x2B])         # BRA $2E7C	    (+43)
    cycles_sub.write(output_rom_buffer)

    cycles_sub.set_location(0x012E5C)  # C12E5C
    cycles_sub.bytestring = bytes([0x80, 0x1E])         # BRA $2E7C	    (+30)
    cycles_sub.write(output_rom_buffer)

    cycles_sub.set_location(0x012E69)  # C12E69
    cycles_sub.bytestring = bytes([
        0x80, 0x11,              # 2E69                   BRA $2E7C	    (+17)
        # Status checker for outline colours.
        0xB9, 0xA9, 0x2E,        # 2E6B/2E6C/2E6D         LDA $2EA9,Y     get current outline in rotation
        0x24, 0x38,              # 2E6E/2E6F              BIT $38         check against current status
        0xD0, 0x10,              # 2E70/2E71              BNE set_color   (+16) branch if a match was found 0x012E82
        0x4A,                    # 2E72                   LSR A           check next status
        0x69, 0x00,              # 2E73/2E74              ADC #$00        maintain wait bit
        0x99, 0xA9, 0x2E,        # 2E75/2E76/2E77         STA $2EA9,Y     update outline colour rotation
        0xC9, 0x04,              # 2E78/2E79              CMP #$20        loop over 6 statuses
        0xB0, 0xF2,              # 2E7A/2E7B              BCS $2E6E       (-14)
        0xA9, 0x80,              # 2E7C/2E7D              LDA #$80        no match found, reset to Rflect
        0x99, 0xA9, 0x2E,        # 2E7E/2E7F/2E80         STA $2EA9,Y
        0x60,                    # 2E81       RTS
        # set_colour
        0x29, 0xFC,              # 2E82/2E83              AND #$FC        clear wait bit
        0x20, 0x0F, 0x1A,        # 2E84/2E85/2E86         JSR $1A0F
        0xBF, 0x8B, 0x2E, 0xC1,  # 2E87/2E88/2E89/2E8A    LDA.l           outline_color_table,X  ; get outline colour
        # outline_color_table
        0x80, 0x36,              # 2D8B/2E8C              BRA $2EC3	    (+54) Implement outline colour
        0x04,                    # 2E8D                   DB $04          Slow
        0x03,                    # 2E8E                   DB $03          Haste
        0x07,                    # 2E8F                   DB $07          Stop
        0x02,                    # 2E90                   DB $02          Shell
        0x01,                    # 2E91                   DB $01          Safe
        0x00,                    # 2E92                   DB $00          Rflect
        0xB9, 0xA9, 0x2E,        # 2E93/2E94/2E95         LDA $2EA9,Y     current outline color rotation
        0x4A,                    # 2E96                   LSR A           move one step forward
        0xB0, 0xE3,              # 2E97/2E98              BCS             reset_rotation (-29) if wait bit set, clear it, reset and exit
        0x29, 0xFC,              # 2E99/2E9A              AND $FC         keep 6 bits
        0xF0, 0xDF,              # 2E9B/2E9C              BEQ             reset_rotation (-11) if all clear, reset and exit
        0x24, 0x38,              # 2E9D/2E9E              BIT             $38 - check current status
        0xF0, 0xF5,              # 2E9F/2EA0              BEQ             rotation_loop (-11) loop until match found
        0x80, 0xDB,              # 2EA1/2EA2              BRA             update_rotation (-37) update outline rotation 0x012E7E
        0xEA, 0xEA, 0xEA, 0xEA,  # 2EA3/2EA4/2EA5/2EA6    NOP
        0xEA, 0xEA, 0xEA, 0xEA,  # 2EA7/2EA8/2EA9/2EAA    NOP
        0xEA, 0xEA, 0xEA, 0xEA,  # 2EAB/2EAC/2EAD/2EAE    NOP
        0xEA, 0xEA, 0xEA, 0xEA,  # 2EAF/2EB0/2EB1/2EB2    NOP
        0xEA                     # 2EB3                   NOP
    ])
    cycles_sub.write(output_rom_buffer)

    cycles_sub.set_location(0x012ECF)  # C12ECF
    cycles_sub.bytestring = bytes([
        # outline_control
        0xBF, 0xAA, 0xE3, 0xC2,  # 2ECF/2ED0/2ED1/2ED2    LDA $C2E3AA,X	Get colour change offset
        0x18,                    # 2ED3                   CLC
        0x65, 0x2C,              # 2ED4/2ED5              ADC $2C		    Add to current fade
        0x85, 0x36,              # 2ED6/2ED7              STA $36		    Save here
        0x29, 0x3C,              # 2ED8/2ED9              AND #$3C	        Isolate fade
        0x4A,                    # 2EDA                   LSR A
        0x85, 0x2C,              # 2EDB/2EDC              STA $2C		    Update fade
        0x64, 0x2D,              # 2EDD/2EDE              STZ $2D
        0xA5, 0x36,              # 2EDF                   LDA $36
        0x0A, 0x0A,              # 2EE1/2EE2              ASL x2		    Is fade decreasing?
        0x90, 0x06,              # 2EE3/2EE4              BCC $2EEB	        (+6) If so...
        0xA9, 0x1F,              # 2EE5/2EE6              LDA #$1F	        ...subtract from 31
        0xE5, 0x2C,              # 2EE7/2EE8              SBC $2C
        0x85, 0x2C,              # 2EE9/2EEA              STA $2C
        0xA5, 0x2C,              # 2EEB/2EEC              LDA $2C		    Get fade amount
        0xC9, 0x1F,              # 2EED/2EEE              CMP #$1F	        Is it fully faded?
        0xD0, 0x06,              # 2EEF/2EF0              BNE $2EF7         (+6) If so...
        0x20, 0x93, 0x2E,        # 2EF1/2EF2              JSR $2E93         ...rotate colour
        0x80, 0x01,              # 2EF3/2EF4              BRA $2EF7	        (+1)
        0xEA                     # 2EF5                   NOP
    ])
    cycles_sub.write(output_rom_buffer)

    cycles_sub.set_location(0x02307D)  # C2307D
    cycles_sub.bytestring = bytes([
        0xDA,                    # 307D                   PHX			    Save party member index
        0xA5, 0xFE,              # 307E/307F              LDA $FE		    Get row
        0x9D, 0xA1, 0x3A,        # 3080/3081/3082         STA $3AA1,X	    Save to special props
        0xBD, 0xD9, 0x3E,        # 3083/3084/3085         LDA $3ED9,X	    Preserve special sprite
        0x48,                    # 3086                   PHA
        0xA3, 0x05,              # 3087/3088              LDA $05,S		    Get loop variable
        0x9D, 0xD9, 0x3E,        # 3089/308A/308B         STA $3ED9,X	    Save to roster position
        0x7B,                    # 308C                   TDC
        0x8A,                    # 308D                   TXA
        0x0A, 0x0A, 0x0A, 0x0A,  # 308E/308F/3090/3091    ASL x4
        0xAA,                    # 3092                   TAX
        0xA9, 0x06,              # 3093/3094              LDA #$06
        0x85, 0xFE,              # 3095/3096              STA $FE
        0x5A,                    # 3097                   PHY			    Preserve Y-loop index
        0xB9, 0x01, 0x16,        # 3098/3099/309A         LDA $1601,Y	    Get normal sprite & name
        0x9D, 0xAE, 0x2E,        # 309B/309C/309D         STA $2EAE,X	    Store to display vars
        0xE8,                    # 309E                   INX
        0xC8,                    # 309F                   INY
        0xC6, 0xFE,              # 30A0/30A1              DEC $FE		    7 iterations to loop
        0x10, 0xF4,              # 30A2/30A3              BPL $3098	        (-12)
        0x7A,                    # 30A4                   PLY			    Restore Y-loop index
        0x68,                    # 30A5                   PLA			    Restore special sprite
        0xC9, 0xFF,              # 30A6/30A7              CMP #$FF		    Is it null?
        0xF0, 0x03,              # 30A8/30A9              BEQ $30AD	        (+3) If not...
        0x9D, 0xA7, 0x2E,        # 30AA/30AB              STA $2EA7,X	    ...overwrite sprite
        0xA9, 0x81,              # 30AC/30AD              LDA #$81		    Reflect + wait bit
        0x9D, 0xA2, 0x2E,        # 30AE/30AF/30B0         STA $2EA2,X	    Init outline rotation
        0xA3, 0x03,              # 30B1/30B2              LDA $03,S		    Get character ID
        0x9D, 0xBF, 0x2E,        # 30B3/30B4/30B5         STA $2EBF,X	    Save it
        0xC9, 0x0E,              # 30B6/30B7              CMP #$0E		    Banon or higher?
        0xC2, 0x20,              # 30B8/30B9              REP #$20		    16-bit A
        0xAA                     # 30BA                   TAX			    Move to X
    ])
    cycles_sub.write(output_rom_buffer)


def no_dance_stumbles(output_rom_buffer: BytesIO):
    nds_sub = Substitution()
    nds_sub.set_location(0x0217A0)  # C217A0
    nds_sub.bytestring = bytes([0xEA, 0xEA])            # No Op x2
    nds_sub.write(output_rom_buffer)


def apply_namingway(output_rom_buffer: BytesIO):
    an_sub = Substitution()
    an_sub.set_location(0xC09AB)
    an_sub.bytestring = bytes([0x4B, 0x4E, 0x00, 0xB6, 0xB5, 0x09, 0x02, 0xB3, 0x5E, 0x00, 0x98, 0x31, 0x96, 0xFE, 0xFD, 0xFD])
    an_sub.write(output_rom_buffer)

    an_sub = Substitution()
    an_sub.set_location(0xC64FA)
    an_sub.bytestring = bytes([0xC0, 0xA4, 0x80, 0x9D, 0x09, 0x02])
    an_sub.write(output_rom_buffer)

def fix_flyaway(output_rom_buffer: BytesIO):
    #Osteoclave's Flyaway Bug event fix
    ff_sub = Substitution()
    ff_sub.set_location(0xACBAD)
    ff_sub.bytestring = bytes([0xFD])
    ff_sub.write(output_rom_buffer)

def item_return_buffer_fix(output_rom_buffer: BytesIO):

    irbf_sub = Substitution()
    irbf_sub.set_location(0x112D5)
    irbf_sub.bytestring = bytes([0xE0, 0x50, 0x00])
    irbf_sub.write(output_rom_buffer)

def change_swdtech_speed(output_rom_buffer: BytesIO, speed: str = "Vanilla"):
    css_sub = Substitution()
    if speed.lower() == "random":
        speed = random.choice(["fastest", "faster", "fast", "Vanilla"])
    if speed.lower() == "fastest":
        swdtech_speed = 0x04
        css_sub.set_location(0x017D84)
        css_sub.bytestring = bytes([0xAD, 0x82, 0x7B, 0x18, 0x69, swdtech_speed, 0x8D, 0x82, 0x7B, 0x80, 0x01, 0xEA])
        css_sub.write(output_rom_buffer)
    elif speed.lower() == "faster":
        swdtech_speed = 0x02
        css_sub.set_location(0x017D84)
        css_sub.bytestring = bytes([0xAD, 0x82, 0x7B, 0x18, 0x69, swdtech_speed, 0x8D, 0x82, 0x7B, 0x80, 0x01, 0xEA])
        css_sub.write(output_rom_buffer)
    elif speed.lower() == "fast":
        swdtech_speed = 0x00
        css_sub.set_location(0x017D87)
        css_sub.bytestring = bytes([swdtech_speed])
        css_sub.write(output_rom_buffer)


# ---------------------
# Memento Mori  07/12/23
#
# Denies relics for unrecruited characters (Moogle Defense, Ghost Train), hiding what the relic will be on the real character
# Unfortunate side-effect: can't peek Mog's relic.
# Enables spell learning from the relic
# ---------------------
def hidden_relic(output_rom_buffer: BytesIO, amount, feature_exclusion_list=None):
    # Gives characters a random relic when the Memento Mori flag is on
    hidden_relic_sub = Substitution()
    hidden_relic_sub.set_location(0x20E9A)
    hidden_relic_sub.bytestring = bytes([
        0x48,  # PHA			; Save the character ID on the stack for now
        0xEB, 0xA9, 0x16, 0x20, 0x81, 0x47, 0xDA, 0xAA, 0xBF, 0xAA, 0x7C, 0xED, 0x8D, 0xAC, 0x11, 0x8D, 0xAD, 0x11,
        0xC2, 0x20, 0xBF, 0xAB, 0x7C, 0xED, 0x8D, 0xBA, 0x11, 0xBF, 0xAD, 0x7C, 0xED, 0xE2, 0x20, 0x8D, 0xA8, 0x11,
        0xEB, 0x8D, 0xAA, 0x11, 0xBF, 0xB5, 0x7C, 0xED, 0x29, 0x03, 0x49, 0x03, 0x1A, 0x1A, 0x8D, 0xDC, 0x11, 0xFA,
        0xA0, 0x06, 0x00,  # ; Code nudged forward by the PHA
        # 0x20ED4
        0x68,  # PLA			; Get the character ID back, necessary for stack preservation
        0x22, 0xCF, 0xB8, 0xC4,
        # JSL $C4B8CF		; Hook: Load character stats, store status byte 1 for imp gear, and then put hidden relic in A
        0x80, 0x08,  # BRA $08          ; Skip two long access hooks used by other Hidden Relic routine
        # 0x20EDB
        0x20, 0x81, 0x47, 0x6B,
        # JSR $4781, RTL        ; 16-bit A = item ID * 30 [size of item data block], long access
        # 0x20EDF
        0x20, 0x4B, 0x60, 0x6B,
        # JSR $604B, RTL        ; Progress towards learning spell for equipped item, long access
        # 0x20EE3
        0x20, 0x9A, 0x0F,  # JSR $0F9A		; Load item properties from character's hidden relic
        # 0x20EE6
        # Vanilla
    ])
    hidden_relic_sub.write(output_rom_buffer)

    if amount == "random":
        amount = random.randint(1, 14)
    iteration = 0

    char_list = sorted(get_characters(), key=lambda char: char.id)[:14]

    # All relics not on rare list or command changer
    relic_list = [0xB0, 0xB1, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xB8, 0xB9, 0xBA, 0xBB, 0xBC, 0xBD, 0xBE, 0xC0, 0xC1,
                  0xC2, 0xC3, 0xC4, 0xC7, 0xC9, 0xCC, 0xCD, 0xD0, 0xD2, 0xD4, 0xD5, 0xD9, 0xE1, 0xE2, 0xE3, 0xE5, 0xE6]
    # Offering, Merit Award, Economizer, Marvel Shoes, Safety Bit, Memento Ring, Ribbon, Moogle Charm, Charm Bangle, Blizzard Orb, Rage Ring, Genji Glove, Exp. Egg, Relic Ring, Pod Bracelet, Muscle Belt
    rare_relic_list = [0xD3, 0xDA, 0xCE, 0xE0, 0xDC, 0xDB, 0xCA, 0xDE, 0xDF, 0xC5, 0xC6, 0xD1, 0xE4, 0xDD, 0xC8, 0xCB]

    #If dearestmolulu is on, don't allow an item with Moogle Charm effect to be innate
    if feature_exclusion_list:
        from itemrandomizer import get_items, STATPROTECT
        for relic in [item for item in get_items() if item.is_relic]:
            # The most convenient way of getting the feature categories
            for feature_type in STATPROTECT.keys():
                for bit in range(8):
                    # Check if the relic has the feature active
                    if relic.features[feature_type] & (0x01 << bit):
                        # Get the friendly name of the feature
                        feature = relic.get_feature(feature_type, 0x01 << bit)
                        # print("Item " + relic.name + " has feature " + str(feature))
                        if feature.lower() in [str(feature).lower() for feature in feature_exclusion_list]:
                            try:
                                # print("Relic found with bad effect " + feature_type + ": " + relic.name)
                                relic_list.remove(relic.itemid)
                                continue
                            except ValueError:
                                pass
                            try:
                                rare_relic_list.remove(relic.itemid)
                            except ValueError:
                                pass

    # Equip Extra Relic
    hidden_relic_sub.set_location(0x4B8CF)
    hidden_relic_sub.bytestring = bytes([
        0x48,  # PHA			; Store character ID on the stack again
        0xBD, 0xF5, 0x15, 0x99, 0xA0, 0x11, 0xE8, 0x88, 0x88, 0x10, 0xF5,  # ; Displaced loop to load character stats
        0xBD, 0xEB, 0x15, 0x85, 0xFE,  # ; Store Status Byte 1 for Imp equipment check
        0xA0, 0x05, 0x00,  # LDY #$0005		; Displaced Y index for later equipment read loop
        0x68,  # PLA			; Fetch back the character ID from the stack
    ])
    hidden_relic_sub.write(output_rom_buffer)

    while iteration < 14:

        char_selection = char_list.pop(random.randint(0, len(char_list) - 1))

        # Set event byte based on character ID
        if char_selection.id >= 8:
            event_byte = 0xDD
            char_bit = int(math.pow(2, char_selection.id - 8))
        else:
            event_byte = 0xDC
            char_bit = int(math.pow(2, char_selection.id))


        if iteration < int(amount):

            if random.randint(1, 10) == 10:
                relic_selection = rare_relic_list.pop(random.randint(0, len(rare_relic_list) - 1))
            else:
                relic_selection = relic_list.pop(random.randint(0, len(relic_list) - 1))
            char_selection.relic_selection = relic_selection
        else:
            char_selection.relic_selection = 0xFF  # Set their relic to Empty

        hidden_relic_sub.set_location(0x4B8E4 + (char_selection.id * 0x11))
        hidden_relic_sub.bytestring = bytes([
            # Character relic checks 0x4B8E4
            0xC9, char_selection.id,  # CMP id
            0xD0, 0x0D,  # BNE $0D
            0xAD, event_byte, 0x1E,  # LDA $1EDC if id < 8, $1EDD if >8     ; shop event bytes
            0x29, char_bit,  # AND math.pow(2, char_selection.id)   ; The power of 2 of the character ID is their bit
            0xD0, 0x03,  # BNE $03   ; If it was nonzero, this character is in the shop
            0x4C, 0xD2, 0xB9,  # JMP $B9D2 ; Elsewise go to the end and set them to empty hidden relic
            0xA9, char_selection.relic_selection,  # LDA
            0x6B,  # RTL       ; JSR to $0F9A, then resume vanilla code
        ])
        hidden_relic_sub.write(output_rom_buffer)

        iteration += 1


    hidden_relic_sub.set_location(0x4B9D2)
    hidden_relic_sub.bytestring = bytes([
        0xA9, 0xFF,  # LDA Empty
        0x6B,  # RTL	         ; JSR to $0F9A, then resume vanilla code
    ])
    hidden_relic_sub.write(output_rom_buffer)

    # Status Screen Display
    hidden_relic_sub.set_location(0x35FC2)
    hidden_relic_sub.bytestring = bytes([
        0x22, 0xA5, 0xFF, 0xC3,  # JSL $C3FFA5  ; Hook: Display hidden relic before reading character stats
    ])
    hidden_relic_sub.write(output_rom_buffer)

    hidden_relic_sub.set_location(0x3FFA5)
    hidden_relic_sub.bytestring = bytes([
        0x48,  # PHA			    ; Save Actor on the stack
        0x22, 0xE4, 0xB8, 0xC4,  # JSL $C4B8E4	    ; Get actor's hidden relic into A
        0x48,  # PHA			    ; Save hidden relic ID on the stack
        0xA0, 0x1D, 0x39,  # LDY #$391D	    ; One row higher than statuses/class name
        0x20, 0x19, 0x35,  # JSR $3519        ; Set pos/WRAM/Y
        0xA9, 0x20,
        0x85, 0x29,  # Set font to player colour
        0x68,  # PLA			    ; Get hidden relic ID back
        0x20, 0xBF, 0xFF,  # JSR $FFBF		; Freespace at the very end of the C3 bank
        0x68,  # PLA			    ; Get Actor back
        0x22, 0x06, 0x00, 0xC2,  # JSL $C20006	    ; Code displaced by the hook
        0x6B,  # RTL
        # 0x3FFBF
        0xC9, 0xFF,  # CMP #$FF		    ; Is the hidden relic empty?
        0xF0, 0x2C,  # BRA $2C		    ; If it is, draw a blank string
        0x08,  # PHP
        0xC2, 0x20,  # REP #$20		    ; Set 16-bit A
        0x48,  # PHA			    ; Put the hidden relic ID on the stack
        0x0A, 0x0A, 0x0A,  # ASL A #3         ; x8
        0x85, 0xE0,  # STA $E0		    ; Store in scratch
        0x68,  # PLA              ; Get hidden relic in A again
        0x48,  # PHA			    ; And store it on the stack again
        0x0A, 0x0A,  # ASL A #2         ; x4
        0x18,  # CLC
        0x65, 0xE0,  # ADC $E0
        0x85, 0xE0,  # STA $E0		    ; $E0 is now hidden relic ID x 12...
        0x68,  # PLA			    ; Get hidden relic in A AGAIN
        0x18,  # CLC
        0x65, 0xE0,  # ADC $E0		    ; Now $E0 is hidden relic ID x 13
        0xAA,  # TAX              ; Index it in X
        0x28,  # PLP			    ; Restore P state, so A is 8-bit again
        0xA0, 0x0D, 0x00,  # LDY #$000D	    ; Loop counter, item strings are 13 characters long
        0xBF, 0x00, 0xB3, 0xD2,  # LDA $D2B300,X	; Hidden relic item name
        0x8D, 0x80, 0x21,  # STA $2180		; Store the current letter in the string
        0xE8,  # INX
        0x88,  # DEY
        0xD0, 0xF5,  # BNE $F5		    ; Loop until all 13 letters are done
        0x9C, 0x80, 0x21,  # STZ $2180		; Mark that the string has ended
        0x4C, 0xD9, 0x7F,  # JMP $7FD9		; Draw the string
        # Empty string branch
        0xA0, 0x0D, 0x00,  # LDY $000D		; Loop counter, the empty string is 13 characters too
        0xA9, 0xFF,  # LDA #$FF		    ; Empty character
        0x8D, 0x80, 0x21,  # STA $2180		; Store the current letter as empty
        0x88,  # DEY
        0xD0, 0xFA,  # BNE $FA		    ; Loop until all 13 letters are blanked
        0x9C, 0x80, 0x21,  # STZ $2180		; Mark that the string has ended
        0x4C, 0xD9, 0x7F,  # JMP $7FD9		; Draw the string
    ])
    hidden_relic_sub.write(output_rom_buffer)

    # Spell Learning from Hidden Relic
    hidden_relic_sub.set_location(0x26025)
    hidden_relic_sub.bytestring = bytes([
        0x5C, 0x9B, 0xB8, 0xC4,  # JML $C4B89B	    ; Hook: Relocate loop check to freespace
    ])
    hidden_relic_sub.write(output_rom_buffer)

    hidden_relic_sub.set_location(0x4B89B)
    hidden_relic_sub.bytestring = bytes([
        0x88,  # DEY              ; Displaced code, check next slot
        0xF0, 0x04,  # BEQ $04          ; If we've checked all slots, continue
        0x5C, 0xF3, 0x5F, 0xC2,  # JML $C25FF3	    ; Otherwise loop to next slot's uncurse and learn routine
        0xC2, 0x20,  # REP #$20         ; Set 16-bit A
        0xA3, 0x05,
        # LDA $05,S        ; Get Y back from C2/5E66. This is a stack relative load! If the routine gets nested deeper, this has to change!
        0xA8,  # TAY              ; Move it from A to Y
        0xE2, 0x20,  # SEP #$20         ; Set 8-bit A
        0xB9, 0xD8, 0x3E,  # LDA $3ED8,Y      ; Get which character this is
        0x22, 0xE4, 0xB8, 0xC4,  # JSL $C4B8E4      ; Load actor's hidden relic into A
        0xC9, 0xFF,  # CMP #$FF         ; Is it empty?
        0xF0, 0x16,  # BEQ $16          ; Exit if so
        0xEB,  # XBA
        0xA9, 0x1E,  # LDA #$1E
        0x22, 0xDB, 0x0E, 0xC2,  # JSL $C20EDB      ; Item ID * 30 -> 16-bit A, long access
        0xAA,  # TAX
        0x7B,  # TDC
        0xBF, 0x04, 0x50, 0xD8,  # LDA $D85004,X    ; Spell the item teaches
        0xA8,  # TAY
        0xBF, 0x03, 0x50, 0xD8,  # LDA $D85003,X    ; Rate spell is learned
        0x22, 0xDF, 0x0E, 0xC2,  # JSL $C20EDF      ; Progress towards learning equipped item spell, long access
        0xFA,  # PLX				; Restore X, displaced by the hook
        0x5C, 0x29, 0x60, 0xC2,  # JML $C26029      ; Exit to vanilla code (goes to RTS)
    ])
    hidden_relic_sub.write(output_rom_buffer)

    hidden_relic_sub.set_location(0x4B85D)
    hidden_relic_sub.bytestring = bytes([0xB9, 0xD8, 0x3E,   # LDA $3ED8,Y    (Which character it is)
        0x22, 0xE4, 0xB8, 0xC4,   # JSL $C4B8E4    (Get this character's hidden relic)
        0xC9, 0xC6,   # CMP #$C6     (Is it Rage Ring?)
        0xF0, 0x0C,   # BEQ yesRage
        0xA9, 0xC6,   # LDA #$C6
        0xD9, 0xD0, 0x3C,   # CMP $3CD0,Y    (Is Relic 1 a Rage Ring?)
        0xF0, 0x05,   # BEQ yesRage
        0xD9, 0xD1, 0x3C,   #CMP $3CD1,Y    (Is Relic 2 a Rage Ring?)
        0xD0, 0x04,   # BNE noRage
        # yesRage:
        0x5C, 0x49, 0x16, 0xC2,   # JML $C21649
        # noRage:
        0x5C, 0x56, 0x16, 0xC2,   # JML $C21656
    ])
    hidden_relic_sub.write(output_rom_buffer)

    hidden_relic_sub.set_location(0x4B87C)
    hidden_relic_sub.bytestring = bytes([0xB9, 0xD8, 0x3E,   # LDA $3ED8,Y    (Which character it is)
        0x22, 0xE4, 0xB8, 0xC4,   # JSL $C4B8E4    (Get this character's hidden relic)
        0xC9, 0xC5,   # CMP #$C5     (Is it Blizzard Orb?)
        0xF0, 0x0C,   # BEQ yesOrb
        0xA9, 0xC5,   # LDA #$C5
        0xD9, 0xD0, 0x3C,   # CMP $3CD0,Y    (Is Relic 1 a Blizzard Orb?)
        0xF0, 0x05,   # BEQ yesOrb
        0xD9, 0xD1, 0x3C,   #CMP $3CD1,Y    (Is Relic 2 a Blizzard Orb?)
        0xD0, 0x04,   # BNE noOrb
        # yesOrb:
        0x5C, 0x62, 0x16, 0xC2,   # JML $C21662
        # noOrb:
        0x5C, 0x66, 0x16, 0xC2,   # JML $C21666
    ])
    hidden_relic_sub.write(output_rom_buffer)

    hidden_relic_sub.set_location(0x2163D)
    hidden_relic_sub.bytestring = bytes([0x5C, 0x5D, 0xB8, 0xC4,   # JML $C4B85D
        0xEA, 0xEA, 0xEA, 0xEA, 0xEA, 0xEA, 0xEA, 0xEA,   # NOP #8
    ])
    hidden_relic_sub.write(output_rom_buffer)

    hidden_relic_sub.set_location(0x21656)
    hidden_relic_sub.bytestring = bytes([0x5C, 0x7C, 0xB8, 0xC4,   # JML $C4B87C
        0xEA, 0xEA, 0xEA, 0xEA, 0xEA, 0xEA, 0xEA, 0xEA,   # NOP #8
    ])
    hidden_relic_sub.write(output_rom_buffer)

def slow_background_scrolling(output_rom_buffer: BytesIO):
    sbs_sub = Substitution()

    #slow scrolling for Clouds
    sbs_sub.set_location(0x2B1B1)
    sbs_sub.bytestring = bytes([0x69, 0x01, 0x00])
    sbs_sub.write(output_rom_buffer)

    #slow scrolling for Waterfall
    sbs_sub.set_location(0x2B1F7)
    sbs_sub.bytestring = bytes([0x69, 0x02, 0x00])
    sbs_sub.write(output_rom_buffer)

def level_cap(output_rom_buffer: BytesIO, maxlevel):

    lc_sub = Substitution()

    lc_sub.bytestring = bytes([maxlevel])

    lc_sub.set_location(0x26074)
    lc_sub.write(output_rom_buffer)

    lc_sub.set_location(0x360A7)
    lc_sub.write(output_rom_buffer)

    lc_sub.set_location(0x0A132)
    lc_sub.write(output_rom_buffer)

    lc_sub.set_location(0x0A136)
    lc_sub.write(output_rom_buffer)

def shadow_stays(output_rom_buffer: BytesIO):
    # Shadow will never leave after combat
    shadow_stays_sub = Substitution()
    shadow_stays_sub.set_location(0x24885)
    shadow_stays_sub.bytestring = bytes([0x80, 0x05]) # BRA $05 ; Always branch, regardless of the state of the Shadow Stays bit
    shadow_stays_sub.write(output_rom_buffer)

def mp_refills(output_rom_buffer: BytesIO):

    mp_refill_sub = Substitution()
    mp_refill_sub.set_location(0x2EAF64)
    mp_refill_sub.bytestring = bytes([0x88, 0x00, 0x08, 0x40, 0x8C, 0x00, 0x7F, 0xFE, 0x88, 0x01, 0x08,
                                      0x40, 0x8C, 0x01, 0x7F, 0xFE, 0x88, 0x02, 0x08, 0x40, 0x8C, 0x02,
                                      0x7F, 0xFE, 0x88, 0x03, 0x08, 0x40, 0x8C, 0x03, 0x7F, 0xFE, 0x88,
                                      0x04, 0x08, 0x40, 0x8C, 0x04, 0x7F, 0xFE, 0x88, 0x05, 0x08, 0x40,
                                      0x8C, 0x05, 0x7F, 0xFE, 0x88, 0x06, 0x08, 0x40, 0x8C, 0x06, 0x7F,
                                      0xFE, 0x88, 0x07, 0x08, 0x40, 0x8C, 0x07, 0x7F, 0xFE, 0x88, 0x08,
                                      0x08, 0x40, 0x8C, 0x08, 0x7F, 0xFE, 0x88, 0x09, 0x08, 0x40, 0x8C,
                                      0x09, 0x7F, 0xFE, 0x88, 0x0A, 0x08, 0x40, 0x8C, 0x0A, 0x7F, 0xFE,
                                      0x88, 0x0B, 0x08, 0x40, 0x8C, 0x0B, 0x7F, 0xFE, 0x88, 0x0C, 0x08,
                                      0x40, 0x8C, 0x0C, 0x7F, 0xFE, 0x88, 0x0D, 0x08, 0x40, 0x8C, 0x0D,
                                      0x7F, 0xFE])
    mp_refill_sub.write(output_rom_buffer)

    mp_refill_patches = {
        0xACBD8: [0xB2, 0x64, 0xAF, 0x24],  # Terra
        0xACBE7: [0xB2, 0x6C, 0xAF, 0x24],  # Locke
        0xACBF6: [0xB2, 0x74, 0xAF, 0x24],  # Cyan
        0xACC05: [0xB2, 0x7C, 0xAF, 0x24],  # Shadow
        0xACC14: [0xB2, 0x84, 0xAF, 0x24],  # Edgar
        0xACC23: [0xB2, 0x8C, 0xAF, 0x24],  # Sabin
        0xACC32: [0xB2, 0x94, 0xAF, 0x24],  # Celes
        0xACC41: [0xB2, 0x9C, 0xAF, 0x24],  # Strago
        0xACC50: [0xB2, 0xA4, 0xAF, 0x24],  # Relm
        0xACC5F: [0xB2, 0xAC, 0xAF, 0x24],  # Setzer
        0xACC6E: [0xB2, 0xBC, 0xAF, 0x24],  # Gau
        0xACC7D: [0xB2, 0xC4, 0xAF, 0x24],  # Gogo
        0xACC8C: [0xB2, 0xCC, 0xAF, 0x24],  # Umaro
        0xACC9B: [0xB2, 0xB4, 0xAF, 0x24]  # Mog
    }
    for location, byte_array in mp_refill_patches.items():
        mp_refill_sub.set_location(location)
        mp_refill_sub.bytestring = bytes(byte_array)
        mp_refill_sub.write(output_rom_buffer)

def change_cursed_shield_battles(output_rom_buffer: BytesIO, amount: int = None):
    if not amount or amount == "random":
        base_cursed_shield_battle_amount = 48
        standard_deviation_number = 16 * RANDOM_MULTIPLIER
        if standard_deviation_number == 0:
            # Tierless - could be anything!
            amount = random.randint(1, 256)
        else:
            amount = max(1, int(random.gauss(base_cursed_shield_battle_amount, standard_deviation_number)))
    else:
        amount = int(amount)

    ccsb_sub = Substitution()
    ccsb_sub.bytestring = bytes([
        0xAD, 0xC0, 0x3E, 0xC9, amount,  # load curse counter and compare to curse count
        0x90, 0x04,                      # skip uncurse if less
        0x22, 0x00, 0xA5, 0xC4,          # Long subroutine to freespace at 0x04A500
    ])
    ccsb_sub.set_location(0x26001)
    ccsb_sub.write(output_rom_buffer)

    ccsb_sub.bytestring = bytes([
        0x9C, 0xC0, 0x3E,              # set curse counter to 0
        0xA9, 0x01, 0x04, 0xF0,        # tell the game a shield was uncursed
        0xA9, 0x67, 0x9D, 0x1F, 0x16,  # replace the cursed shield with a paladin shield
        0x6B                           # return from long subroutine
    ])
    ccsb_sub.set_location(0x4A500)
    ccsb_sub.write(output_rom_buffer)

def improved_party_gear(output_rom_buffer: BytesIO, myself_name_address, myself_name_bank):
    # On the party gear display screen, display the original character slot name
    # and their equipped esper.  This is similar to the functionality of RotDS,
    # but we add the character slot name for Beyond Chaos since it's useful.
    ipg_sub = Substitution()
    ipg_sub.set_location(0x038F04)
    ipg_sub.bytestring = bytes([
        # We start overwriting from the beginning of the routine to draw party gear.
        # The original code has four subroutines that each do the same thing except
        # read different addresses for the character slots.  This is a waste of space
        # for non-time-critical code.  We can overwrite these four routines by
        # replacing their functionality with a loop.  Note that these four
        # subroutines follow the routine at C38EED, so we can just keep writing.
        #
        # Start at first slot.
        0x64, 0x28,                 # STZ.B $28
        # Initialize extra palette color.  The original game doesn't use this
        # palette for anything in the menu system, so make it yellow.
        0x22, 0x01, 0xAF, 0xEE,     # JSL yellow_palette
                                # member_loop:
        # Clear high part of A.
        0xA9, 0x00,                 # LDA.B #0
        0xEB,                       # XBA
        # Is anyone in this slot?
        0xA5, 0x28,                 # LDA.B $28
        0xAA,                       # TAX
        0xB5, 0x69,                 # LDA.B $69,x
        0x30, 0x60,                 # BMI nobody
        # Save the character ID.
        0x48,                       # PHA
        # While we have the slot in A, let's do some things.
        # Double slot and give to Y.  Clears carry because slot < 128.
        0x8A,                       # TXA
        0x0A,                       # ASL
        0xA8,                       # TAY
        # Calculate high byte of text position for this slot:
        # $390D + (slot * $200).
        0x69, 0x39,                 # ADC.B #$39
        0xEB,                       # XBA
        0xA9, 0x0D,                 # LDA.B #$0D
        # Copy actor's address.  They're words at 69, 6B, 6D, 6F.
        0xB6, 0x6D,                 # LDX.B $6D,y
        0x86, 0x67,                 # STX.B $67
        # Set palette to cyan and draw actor's name.
        # Y = text address (the 390D calculation above).
        0xA8,                       # TAY
        0x5A,                       # PHY
        0xA9, 0x24,                 # LDA.B #$24
        0x85, 0x29,                 # STA.B $29
        0x20, 0xCF, 0x34,           # JSR.W $C334CF
        0x7A,                       # PLY
        # Palette for slot name.
        0xA9, 0x28,                 # lda.b #$28
        0x85, 0x29,                 # sta.b $29
        # Compute tile address for slot's name.
        0xC2, 0x21,                 # REP #$21   ; clear carry too
        0x98,                       # TYA
        0x69, 0x10, 0x00,           # ADC.W #8 * 2
        0x8F, 0x89, 0x9E, 0x7E,     # STA.L $7E9E89
        # Set up parameters for fixed-size table.
        0xA9, 0x08, 0x00,           # LDA.W #8
        0x85, 0xEB,                 # STA.B $EB
        0xA9] + myself_name_address + [ # LDA.W #myself_name_address & $FFFF
        0x85, 0xEF,                 # STA.B $EF
        0xE2, 0x20,                 # SEP #$20
        0xA9] + myself_name_bank + [# LDA.B #myself_name_bank
        0x85, 0xF1,                 # STA.B $F1
        # Get back the character ID.
        0x68,                       # PLA
        # Don't draw slot's name if not a usual character.
        0xC9, 0x0E,                 # CMP.B #14
        0xB0, 0x08,                 # BCS special_character
        # Copy fixed-size string to write buffer.
        # A = index of fixed-size string, just set.
        0x5A,                       # PHY
        0x20, 0x67, 0x84,           # JSR.W $C38467
        # Draw write buffer to tilemap.
        0x20, 0xD9, 0x7F,           # JSR.W $C37FD9
        0x7A,                       # PLY
                                # special_character:
        # Use special yellow palette.
        0xA9, 0x34,                 # LDA.B #$34
        0x85, 0x29,                 # STA.B $29
        # Draw esper's name.
        # Get tilemap address and move over 18 tiles.
        0xC2, 0x21,                 # REP #$21   ; clear carry too
        0x98,                       # TYA
        0x69, 0x20, 0x00,           # ADC.W #16 * 2
        0xA8,                       # TAY
        0xE2, 0x20,                 # SEP #$20
        # This routine wants the actor address in D+$67 and tilemap in Y.
        0x20, 0xE6, 0x34,           # JSR.W $C334E6
        # Reset palette to normal.
        0xA9, 0x20,                 # LDA.B #$20
        0x85, 0x29,                 # STA.B $29
        # Draw gear for this party member.
        # Row = 4 + (slot * 8).
        0xA5, 0x28,                 # LDA.B $28
        0x0A,                       # ASL
        0x0A,                       # ASL
        0x0A,                       # ASL
        0x69, 0x04,                 # ADC.B #$04
        0x20, 0x8A, 0x8F,           # JSR.W $C38F8A
        # Next party member.
                                # nobody:
        0xA5, 0x28,                 # LDA.B $28
        0x1A,                       # INC
        0x85, 0x28,                 # STA.B $28
        0xC9, 0x04,                 # CMP.B #4
        0xD0, 0x8D,                 # BNE member_loop
        # Do stuff from the original code after the menu draws.
        0x20, 0x28, 0x0E,           # JSR.W $C30E28
        0x20, 0x36, 0x0E,           # JSR.W $C30E36
        0x20, 0x3C, 0x6A,           # JSR.W $C36A3C
        0x4C, 0x6E, 0x0E])          # JMP.W $C30E6E
    ipg_sub.write(output_rom_buffer)

    # The subroutine writes the yellow color palette on top of an
    # existing palette that wasn't being used in the menu.
    # It's here because it didn't fit in the above code cave.
    ipg_sub.set_location(0x2EAF01)
    ipg_sub.bytestring = bytes([
                                # yellow_palette:
        0xC2, 0x20,                 # REP $20
        0xA9, 0x00, 0x00,           # LDA.W #$0000
        0x8F, 0xE9, 0x30, 0x7E,     # STA.L $7E3049 + (((5 * 16) + 0) * 2)
        0x8F, 0xEB, 0x30, 0x7E,     # STA.L $7E3049 + (((5 * 16) + 1) * 2)
        0xA9, 0xCE, 0x39,           # LDA.W #$39CE
        0x8F, 0xED, 0x30, 0x7E,     # STA.L $7E3049 + (((5 * 16) + 2) * 2)
        0xA9, 0xBF, 0x03,           # LDA.W #$03BF
        0x8F, 0xEF, 0x30, 0x7E,     # STA.L $7E3049 + (((5 * 16) + 3) * 2)
        0xE2, 0x20,                 # SEP #$20
        0x6B])                      # RTL
    ipg_sub.write(output_rom_buffer)

def y_equip_relics(output_rom_buffer: BytesIO):
    y_equip_relics_sub = Substitution()
    y_equip_relics_sub.set_location(0x30247)
    y_equip_relics_sub.bytestring = bytes([0x1e, 0x96])
    y_equip_relics_sub.write(output_rom_buffer)

    y_equip_relics_sub.set_location(0x30287)
    y_equip_relics_sub.bytestring = bytes([0xcd, 0x98])
    y_equip_relics_sub.write(output_rom_buffer)

    y_equip_relics_sub.set_location(0x31be9)
    y_equip_relics_sub.bytestring = bytes([0x5b, 0x96])
    y_equip_relics_sub.write(output_rom_buffer)

    y_equip_relics_sub.set_location(0x31bf7)
    y_equip_relics_sub.bytestring = bytes([0x60, 0x96])
    y_equip_relics_sub.write(output_rom_buffer)

    y_equip_relics_sub.set_location(0x3960d)
    y_equip_relics_sub.bytestring = bytes([0x65, 0x96])
    y_equip_relics_sub.write(output_rom_buffer)

    y_equip_relics_sub.set_location(0x39615)
    y_equip_relics_sub.bytestring = bytes([0x0c, 0x96, 0xe6, 0x3a, 0xa9, 0x2c, 0x85, 0x29, 0x60, 0x20, 0x0c, 0x96, 0x20, 0x4e, 0x90, 0x20, 0x56, 0x8e, 0xa5, 0x08, 0x10, 0x0b, 0x20, 0xb2, 0x0e, 0x7b, 0xa5, 0x4b, 0x0a, 0xaa, 0x7c, 0x6c, 0x96, 0xa5, 0x09, 0x10, 0x0d, 0x20, 0xa9, 0x0e, 0x20, 0x10, 0x91, 0xa9, 0x04, 0x85, 0x27, 0x64, 0x26, 0x60, 0x0a, 0x10, 0x0a, 0x20, 0xb2, 0x0e, 0xa9, 0x58, 0x85, 0x26, 0xe6, 0x25, 0x60, 0xa9, 0x35, 0x85, 0xe0, 0x4c, 0x22, 0x20, 0xa0, 0x09, 0xa3, 0x80, 0x08, 0xa0, 0x11, 0xa3, 0x80, 0x03, 0xa0, 0xea, 0xa2, 0x4c, 0xf9, 0x02, 0x60])
    y_equip_relics_sub.write(output_rom_buffer)

    y_equip_relics_sub.set_location(0x39672)
    y_equip_relics_sub.bytestring = bytes([0x9a])
    y_equip_relics_sub.write(output_rom_buffer)
    y_equip_relics_sub.set_location(0x39678)
    y_equip_relics_sub.bytestring = bytes([0x5b])
    y_equip_relics_sub.write(output_rom_buffer)
    y_equip_relics_sub.set_location(0x39692)
    y_equip_relics_sub.bytestring = bytes([0x60, 0x96, 0x20, 0x7a, 0x96, 0xe6, 0x26, 0x60, 0x20, 0xa8, 0x96, 0x80, 0xe9, 0xa9, 0x35, 0x85, 0x26, 0x64, 0x27, 0xc6, 0x25])
    y_equip_relics_sub.write(output_rom_buffer)

    y_equip_relics_sub.set_location(0x3988c)
    y_equip_relics_sub.bytestring = bytes([0x10, 0x21, 0x20, 0xb2, 0x0e, 0xa5, 0x4e, 0x85, 0x5f, 0xa2, 0x57, 0x55, 0x86, 0x26, 0x20, 0x59, 0x9b, 0x20, 0x50, 0xa1, 0x20, 0xeb, 0x9a, 0x20, 0x33, 0x92, 0x20, 0x15, 0x6a, 0x20, 0x68, 0x13, 0x4c, 0xac, 0x9c, 0xa5, 0x09, 0x10, 0x0d, 0x20, 0xa9, 0x0e, 0xa9, 0x36, 0x85, 0x26, 0x20, 0x50, 0x8e, 0x4c, 0x59, 0x8e, 0x0a, 0x10, 0x03, 0x4C, 0x4A, 0x96, 0xA5, 0x26, 0x69, 0x29, 0x4C, 0x56, 0x96, 0x20, 0x72, 0x8E, 0xA5, 0x08, 0x10, 0xDB, 0x20, 0xB2, 0x0E, 0x20, 0xF2, 0x93, 0xC2, 0x21, 0x98, 0xE2, 0x20, 0x65, 0x4B, 0xA8, 0xB9, 0x1F, 0x00, 0x20, 0x5E, 0x9D, 0xA9, 0xFF, 0x99, 0x1F, 0x00, 0x20, 0x1B, 0x91, 0x80, 0xBD, 0xA5, 0x09, 0x0A, 0x10, 0x14, 0x20, 0xB2, 0x0E, 0x20, 0x5F, 0x1E, 0xB0, 0x0A, 0x20, 0xEB, 0x9E, 0xA5, 0x99, 0xD0, 0x03, 0x20, 0x9F, 0x96, 0x64, 0x08, 0x4C, 0xE6, 0x9E, 0xEA])
    y_equip_relics_sub.write(output_rom_buffer)

    y_equip_relics_sub.set_location(0x39e81)
    y_equip_relics_sub.bytestring = bytes([0x5b])
    y_equip_relics_sub.write(output_rom_buffer)

    y_equip_relics_sub.set_location(0x39e8f)
    y_equip_relics_sub.bytestring = bytes([0x60])
    y_equip_relics_sub.write(output_rom_buffer)

    y_equip_relics_sub.set_location(0x39edd)
    y_equip_relics_sub.bytestring = bytes([0xf2, 0x98])
    y_equip_relics_sub.write(output_rom_buffer)

    y_equip_relics_sub.set_location(0x39f1d)
    y_equip_relics_sub.bytestring = bytes([0x65])
    y_equip_relics_sub.write(output_rom_buffer)

    y_equip_relics_sub.set_location(0x39fdf)
    y_equip_relics_sub.bytestring = bytes([0x5b])
    y_equip_relics_sub.write(output_rom_buffer)

    y_equip_relics_sub.set_location(0x39ff0)
    y_equip_relics_sub.bytestring = bytes([0x60])
    y_equip_relics_sub.write(output_rom_buffer)

    y_equip_relics_sub.set_location(0x3a048)
    y_equip_relics_sub.bytestring = bytes([0xf2, 0x98])
    y_equip_relics_sub.write(output_rom_buffer)

    y_equip_relics_sub.set_location(0x3a147)
    y_equip_relics_sub.bytestring = bytes([0xf2, 0x98])
    y_equip_relics_sub.write(output_rom_buffer)


def fix_gogo_portrait(output_rom_buffer: BytesIO):
    """Hides the portion of Gogo's portrait that shows incorrectly on his status menu."""
    output_rom_buffer.seek(0x35f51)
    output_rom_buffer.write(bytes([0x0a, 0x62]))


def patch_doom_gaze(output_rom_buffer: BytesIO):
    # Add an option to the Falcon's wheel to search out Doom Gaze
    sub = Substitution()
    sub.set_location(0xA009D)
    sub.bytestring = bytes([0xb2, 0x1f, 0xaf, 0x24])
    sub.write(output_rom_buffer)

    # Handles String selection
    sub.set_location(0xAF56E)
    sub.bytestring = bytes([0xb2, 0x26, 0xaf, 0x24, 0xfe, 0xfd, 0xfd, 0xfd, 0xfd, 0xfd])
    sub.write(output_rom_buffer)

    # Doom Gaze airship search option helper
    sub.set_location(0x2EAF1F)
    sub.bytestring = bytes([0x3D, 0x12, 0x41, 0x12, 0xD0, 0xE2, 0xFE,
                            0xC1, 0xE2, 0x80, 0xA4, 0x00, 0x3C, 0xAF, 0x24,
                            0x4B, 0x60, 0x80, 0xB6, 0x8D, 0xF5, 0x00, 0x46, 0xAF, 0x24,
                            0xB3, 0x5E, 0x00, 0xFE,
                            0x4B, 0x2A, 0x85, 0xB6, 0x8D, 0xF5, 0x00, 0xB3, 0x5E, 0x00,
                            0x5A, 0x08, 0x5C, 0x6B, 0x11, 0x20, 0x11, 0x08, 0xC0,
                            0x4D, 0x5D, 0x29, 0xF0, 0x4C, 0xB2, 0xA9, 0x5E, 0x00,
                            0xB7, 0x48, 0x83, 0x04, 0x00, 0x96, 0xC0, 0x27, 0x01, 0x9D, 0x00, 0x00])
    sub.write(output_rom_buffer)


def nicer_poison(output_rom_buffer: BytesIO):
    # make poison pixelation effect 1/10 of it's vanilla amount in dungeons/towns
    nicer_poison_sub = Substitution()
    nicer_poison_sub.set_location(0x00E82)
    nicer_poison_sub.bytestring = bytes([0x0F, 0x0F, 0x0F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F,
                                         0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F,
                                         0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x0F, 0x0F, 0x0F])
    nicer_poison_sub.write(output_rom_buffer)

    # remove poison pixelation on the overworld
    nicer_poison_sub.set_location(0x2E1864)
    nicer_poison_sub.bytestring = bytes([0xA9, 0x00])
    nicer_poison_sub.write(output_rom_buffer)


def fewer_flashes(output_rom_buffer: BytesIO, flag_value):
    anti_seizure_sub = Substitution()

    if not flag_value.lower() == "bumrush":
        # ------------- Attack Animations -------------
        #
        # Removing Final Kefka Death Flashing
        #
        anti_seizure_sub.set_location(0x10023B)  # D0023B
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x100241)  # D00241
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x100249)  # D00249
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10024F)  # D0024F
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Boss Death Flashing
        #
        anti_seizure_sub.set_location(0x100477)  # D00477
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10047D)  # D0047D
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x100485)  # D00485
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x100498)  # D00498
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Magicite Transformation Flash
        #
        anti_seizure_sub.set_location(0x100F31)  # D00F31
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x100F40)  # D00F40
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Ice 3 Flash
        #
        anti_seizure_sub.set_location(0x101979)  # D01979
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10197C)  # D0197C
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10197F)  # D0197F
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x101982)  # D01982
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x101985)  # D01985
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x101988)  # D01988
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10198B)  # D0198B
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10198E)  # D0198E
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x101991)  # D01991
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Fire 3 Flash
        #
        anti_seizure_sub.set_location(0x1019FB)  # D019FB
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x101A1D)  # D01A1D
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Phantasm Flash
        #
        anti_seizure_sub.set_location(0x101E08)  # D01E08
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x101E0E)  # D01E0E
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x101E20)  # D01E20
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x101E28)  # D01E28
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Tiger Break Flash
        #
        anti_seizure_sub.set_location(0x10240E)  # D0240E
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x102412)  # D02412
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x102416)  # D02416
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Diffuser Flash
        #
        anti_seizure_sub.set_location(0x103AEB)  # D03AEB
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x103AEE)  # D03AEE
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x103AF1)  # D03AF1
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x103AF4)  # D03AF4
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x103AF7)  # D03AF7
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x103AFA)  # D03AFA
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x103AFD)  # D03AFD
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x103B00)  # D03B00
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x103B03)  # D03B00
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Cat Rain Flash
        #
        anti_seizure_sub.set_location(0x102678)  # D02678
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10267C)  # D0267C
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Unknown Script 1's Flash
        #
        anti_seizure_sub.set_location(0x1026EF)  # D026EF
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1026FB)  # D026FB
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Mirager Flash
        #
        anti_seizure_sub.set_location(0x102792)  # D02792
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x102796)  # D02796
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Sabre Soul Flash
        #
        anti_seizure_sub.set_location(0x1027D4)  # D027D4
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1027DB)  # D027DB
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Back Blade Flash
        #
        anti_seizure_sub.set_location(0x1028D4)  # D028D4
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1028E0)  # D028E0
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Royal Shock Flash
        #
        anti_seizure_sub.set_location(0x102968)  # D02968
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10296C)  # D0296C
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x102974)  # D02974
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Unknown Script 2's Flash
        #
        anti_seizure_sub.set_location(0x102AAE)  # D02AAE
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x102AB2)  # D02AB2
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Absolute Zero Flash
        #
        anti_seizure_sub.set_location(0x102BFF)  # D02BFF
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x102C03)  # D02C03
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Unknown Script 3's Flash
        #
        anti_seizure_sub.set_location(0x1030CB)  # D030CB
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1030CF)  # D030CF
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Reverse Polarity Flash
        #
        anti_seizure_sub.set_location(0x10328C)  # D0328C
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x103293)  # D03293
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Rippler Flash
        #
        anti_seizure_sub.set_location(0x1033C7)  # D033C7
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1033CB)  # D033CB
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Step Mine Flash
        #
        anti_seizure_sub.set_location(0x1034DA)  # D034DA
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1034E1)  # D034E1
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Unknown Script 4's Flash
        #
        anti_seizure_sub.set_location(0x1035E7)  # D035E7
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1035F7)  # D035F7
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Schiller Flash
        #
        anti_seizure_sub.set_location(0x10380B)
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        # This commented out code is for vanilla Schiller, which BC is no longer using
        # anti_seizure_sub.set_location(0x10381A)  # D0381A
        # anti_seizure_sub.bytestring = bytes([0xE0])
        # anti_seizure_sub.write(output_rom_buffer)

        # anti_seizure_sub.set_location(0x10381E)  # D0381E
        # anti_seizure_sub.bytestring = bytes([0xF0])
        # anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Wall Change Flash
        #
        anti_seizure_sub.set_location(0x10399F)  # D0399F
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1039A4)  # D039A4
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1039AA)  # D039AA
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1039B0)  # D039B0
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1039B6)  # D039B6
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1039BC)  # D039BC
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1039C2)  # D039C2
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1039C8)  # D039C8
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1039CE)  # D039CE
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1039D5)  # D039D5
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Ultima Flash
        #
        anti_seizure_sub.set_location(0x1056EE)  # D056EE
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1056F6)  # D056F6
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Bolt 3/Giga Volt Flash
        #
        anti_seizure_sub.set_location(0x10588F)  # D0588F
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x105894)  # D05894
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x105897)  # D05897
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10589A)  # D0589A
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10589D)  # D0589D
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1058A2)  # D058A2
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1058A7)  # D058A7
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1058AC)  # D058AC
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1058B1)  # D058B1
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing X-Zone Flash
        #
        anti_seizure_sub.set_location(0x105A5E)  # D05A5E
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x105A6B)  # D05A6B
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x105A7A)  # D05A7A
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Dispel Flash
        #
        anti_seizure_sub.set_location(0x105DC3)  # D05DC3
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x105DCA)  # D05DCA
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x105DD3)  # D05DD3
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x105DDC)  # D05DDC
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x105DE5)  # D05DE5
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x105DEE)  # D05DEE
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Pep Up/Break Flash
        #
        anti_seizure_sub.set_location(0x1060EB)  # D060EB
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1060EF)  # D060EF
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Shock Flash
        #
        anti_seizure_sub.set_location(0x1068BF)  # D068BF
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1068D1)  # D068D1
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Quadra Slam/Slice Flash
        #
        # White Flash
        anti_seizure_sub.set_location(0x1073DD)  # D073DD
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1073EF)  # D073EF
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1073F4)  # D073F4
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        # Green Flash
        anti_seizure_sub.set_location(0x107403)  # D07403
        anti_seizure_sub.bytestring = bytes([0x40])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x107425)  # D07425
        anti_seizure_sub.bytestring = bytes([0x50])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10742A)  # D0742A
        anti_seizure_sub.bytestring = bytes([0x50])
        anti_seizure_sub.write(output_rom_buffer)

        # Blue Flash
        anti_seizure_sub.set_location(0x107437)  # D07437
        anti_seizure_sub.bytestring = bytes([0x20])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x107459)  # D07459
        anti_seizure_sub.bytestring = bytes([0x30])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10745E)  # D0745E
        anti_seizure_sub.bytestring = bytes([0x30])
        anti_seizure_sub.write(output_rom_buffer)

        # Red Flash
        anti_seizure_sub.set_location(0x107491)  # D07491
        anti_seizure_sub.bytestring = bytes([0x80])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1074B3)  # D074B3
        anti_seizure_sub.bytestring = bytes([0x90])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1074B8)  # D074B8
        anti_seizure_sub.bytestring = bytes([0x90])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Slash Flash
        #
        anti_seizure_sub.set_location(0x1074F5)  # D074F5
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1074FE)  # D074FE
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x107508)  # D07508
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Flash Flash
        #
        anti_seizure_sub.set_location(0x107851)  # D07851
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10785D)  # D0785D
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Removing Goner Flash
        #
        anti_seizure_sub.set_location(0x1000D8)  # D000D8
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1000DA)  # D000DA
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1000DC)  # D000DC
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1000DE)  # D000DE
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1000E0)  # D000E0
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1000E6)  # D000E6
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1000E8)  # D000E8
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x100173)  # D00173
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x100176)  # D00176
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x100179)  # D00179
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        # BG3 horizontal lines fade to black
        anti_seizure_sub.set_location(0x1001BD)  # D001BD
        anti_seizure_sub.bytestring = bytes([0xCF])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x1001BF)  # D001BF
        anti_seizure_sub.bytestring = bytes([0xB4])
        anti_seizure_sub.write(output_rom_buffer)

        # ------------- Battle Event Scripts -------------
        #
        # Battle Event Script $15
        #
        anti_seizure_sub.set_location(0x10B887)  # D0B887
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10B88D)  # D0B88D
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10B894)  # D0B894
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10B89A)  # D0B89A
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10B8A1)  # D0B8A1
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10B8A7)  # D0B8A7
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10B8AE)  # D0B8AE
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10B8B4)  # D0B8B4
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10BCF5)  # D0BCF5
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10BCF9)  # D0BCF9
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Battle Event Script $19
        #
        anti_seizure_sub.set_location(0x10C7A4)  # D0C7A4
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10C7AA)  # D0C7AA
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10C7B1)  # D0C7B1
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10C7B7)  # D0C7B7
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10C7BE)  # D0C7BE
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10C7C4)  # D0C7C4
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10C7CB)  # D0C7CB
        anti_seizure_sub.bytestring = bytes([0xE0])
        anti_seizure_sub.write(output_rom_buffer)

        anti_seizure_sub.set_location(0x10C7D1)  # D0C7D1
        anti_seizure_sub.bytestring = bytes([0xF0])
        anti_seizure_sub.write(output_rom_buffer)

        #
        # Thamasa Attack - Kefka Kills Espers
        #

        anti_seizure_sub.set_location(0xC03CA)
        anti_seizure_sub.bytestring = bytes([0xFD, 0xFD])
        anti_seizure_sub.write(output_rom_buffer)

    #
    # Removing Bum Rush Flashes
    #
    # Flash 1
    anti_seizure_sub.set_location(0x106C7F)  # D06C7F
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(output_rom_buffer)

    anti_seizure_sub.set_location(0x106C88)  # D06C88
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(output_rom_buffer)

    # Flash 2
    anti_seizure_sub.set_location(0x106C96)  # D06C96
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(output_rom_buffer)

    anti_seizure_sub.set_location(0x106C9F)  # D06C9F
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(output_rom_buffer)

    # Other Bum Rush Background Sets - possibly unnecessary
    anti_seizure_sub.set_location(0x106C3F)  # D06C3F
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(output_rom_buffer)

    anti_seizure_sub.set_location(0x106C48)  # D06C48
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(output_rom_buffer)

    anti_seizure_sub.set_location(0x106C54)  # D06C54
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(output_rom_buffer)

    anti_seizure_sub.set_location(0x106C88)  # D06C87
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(output_rom_buffer)

    #
    # Duncan Bum Rush Cut Scene Flashes
    #

    anti_seizure_sub.set_location(0xC0469)
    anti_seizure_sub.bytestring = bytes([0xFD, 0xFD])
    anti_seizure_sub.write(output_rom_buffer)

    anti_seizure_sub.set_location(0xC0D12)
    anti_seizure_sub.bytestring = bytes([0xFD, 0xFD])
    anti_seizure_sub.write(output_rom_buffer)

    anti_seizure_sub.set_location(0xC0D5F)
    anti_seizure_sub.bytestring = bytes([0xFD, 0xFD])
    anti_seizure_sub.write(output_rom_buffer)

    anti_seizure_sub.set_location(0xC0D7F)
    anti_seizure_sub.bytestring = bytes([0xFD, 0xFD])
    anti_seizure_sub.write(output_rom_buffer)

    anti_seizure_sub.set_location(0xC0D9F)
    anti_seizure_sub.bytestring = bytes([0xFD, 0xFD])
    anti_seizure_sub.write(output_rom_buffer)

    anti_seizure_sub.set_location(0xC0DF0)
    anti_seizure_sub.bytestring = bytes([0xFD, 0xFD])
    anti_seizure_sub.write(output_rom_buffer)

    anti_seizure_sub.set_location(0xC0E09)
    anti_seizure_sub.bytestring = bytes([0xFD, 0xFD])
    anti_seizure_sub.write(output_rom_buffer)

    anti_seizure_sub.set_location(0xC0E22)
    anti_seizure_sub.bytestring = bytes([0xFD, 0xFD])
    anti_seizure_sub.write(output_rom_buffer)

    anti_seizure_sub.set_location(0xC0E3B)
    anti_seizure_sub.bytestring = bytes([0xFD, 0xFD])
    anti_seizure_sub.write(output_rom_buffer)

    anti_seizure_sub.set_location(0xC0E65)
    anti_seizure_sub.bytestring = bytes([0xFD, 0xFD])
    anti_seizure_sub.write(output_rom_buffer)

    anti_seizure_sub.set_location(0xC0E74)
    anti_seizure_sub.bytestring = bytes([0xFD, 0xFD])
    anti_seizure_sub.write(output_rom_buffer)

    # ------------- Event Scripts -------------
    # CA/00D6 - White Flash
    # CA/0A35 - White Flash
    # CA/0E98 - End Color Effects
    # CA/0F6C - End Color Effects
    # CA/144F - White Flash
    # CA/15F7 - White Flash
    # CA/49D3 - White Flash
    # CA/49F1 - White Flash
    # CA/49FA - White Flash
    # CA/4AEC - White Flash
    # CA/4E3F - White Flash
    # CA/4FB3 - Blue Flash
    # CA/5BF9 - White Flash
    # CA/5C19 - White Flash
    # CA/74AE - End Color Effects
    # CA/9A2A - White Flash
    # CA/A393 - White Flash
    # CA/D033 - White Flash
    # CA/E020 - White Flash
    # CA/E023 - White Flash
    # CA/E442 - White Flash
    # CA/E45E - White Flash
    # CB/1277 - End Color Effects
    # CB/225E - Blue Flash
    # CB/2DC7 - Red Flash
    # CB/2DDE - Red Flash
    # CB/2DEF - Red Flash
    # CB/3E0E - White Flash
    # CB/3E59 - White Flash
    # CB/47D3 - Red Flash
    # CB/481F - Red Flash
    # CB/4C55 - Red Flash
    # CB/4D10 - White Flash
    # CB/6904 - Red Flash
    # CB/7DA1 - Blue Flash
    # CB/8BA2 - Blue Flash
    # CB/8BA7 - Blue Flash
    # CB/8BB8 - Yellow Flash
    # CB/8BBB - Yellow Flash
    # CB/8BD7 - Red Flash
    # CB/8BDA - Red Flash
    # CB/9552 - Red Flash
    # CB/955A - Red Flash
    # CB/9567 - Red Flash
    # CB/956D - Red Flash
    # CB/9865 - Red Flash
    # CB/9888 - Red Flash
    # CB/9939 - White Flash
    # CB/9944 - White Flash
    # CB/9952 - White Flash
    # CB/9975 - White Flash
    # CB/99A9 - White Flash
    # CB/9A47 - White Flash
    # CB/A3EE - White Flash
    # CB/B14C - Blue Flash
    # CB/F6CD - Blue Flash
    # CB/F6D3 - Blue Flash
    # CB/F6D9 - End Color Effects
    # CB/F6EC - End Color Effects
    # CB/F6F3 - End Color Effects
    # CB/F700 - End Color Effects
    # CB/FBFE - Red Flash
    # CB/FC02 - Red Flash
    # CB/FC18 - Red Flash
    # CB/FC49 - Red Flash
    # CB/FC4D - Red Flash
    # CB/FC7B - Red Flash
    # CB/FCE2 - Yellow Flash
    # CB/FCE5 - Yellow Flash
    # CB/FCE8 - Yellow Flash
    # CB/FCF1 - Yellow Flash
    # CB/FCF8 - Yellow Flash
    # CB/FD01 - Yellow Flash
    # CB/FD06 - Yellow Flash
    # CB/FD75 - Blue Flash
    # CB/FD78 - Blue Flash
    # CB/FD7B - Blue Flash
    # CB/FD84 - Blue Flash
    # CB/FD91 - Blue Flash
    # CB/FD9A - Blue Flash
    # CB/FD9D - Blue Flash
    # CB/FDF5 - Red Flash
    # CB/FDF8 - Red Flash
    # CB/FDFB - Red Flash
    # CB/FE04 - Red Flash
    # CB/FE11 - Red Flash
    # CB/FE1A - Red Flash
    # CB/FE1D - Red Flash
    # CB/FE88 - Red Flash
    # CB/FE8C - Red Flash
    # CB/FE8F - Red Flash
    # CB/FE95 - Red Flash
    # CB/FE99 - Red Flash
    # CB/FEEB - Red Flash
    # CB/FEEF - Red Flash
    # CC/00A2 - Red Flash
    # CC/00A7 - Yellow Flash
    # CC/00AC - Cyan Flash
    # CC/00B1 - Magenta Flash
    # CC/00B6 - Red Flash
    # CC/018B - White Flash
    # CC/0190 - White Flash
    # CC/01A2 - White Flash
    # CC/01CA - End Color Effects
    # CC/01F2 - End Color Effects
    # CC/01F6 - White Flash
    # CC/023F - Yellow Flash
    # CC/0246 - Yellow Flash
    # CC/029E - Magenta Flash
    # CC/02A5 - Magenta Flash
    # CC/02DA - Red Flash
    # CC/02DF - Yellow Flash
    # CC/02E4 - Cyan Flash
    # CC/02E9 - Magenta Flash
    # CC/02EE - Red Flash
    # CC/03AC - Red Flash
    # CC/03B1 - Green Flash
    # CC/03B6 - Yellow Flash
    # CC/03BB - Blue Flash
    # CC/03C0 - Magenta Flash
    # CC/03C5 - Cyan Flash
    # CC/03CA - White Flash
    # CC/0469 - White Flash
    # CC/0D12 - White Flash
    # CC/0D5F - White Flash
    # CC/0D7F - White Flash
    # CC/0D9F - White Flash
    # CC/0DF0 - White Flash
    # CC/0E09 - White Flash
    # CC/0E22 - White Flash
    # CC/0E3B - White Flash
    # CC/0E65 - White Flash
    # CC/0E74 - White Flash
    # CC/1AEA - Red Flash
    # CC/1B51 - Red Flash
    # CC/1BB9 - Red Flash
    # CC/1D80 - Red Flash
    # CC/1DAB - Red Flash
    # CC/1E0A - Red Flash
    # CC/1EA7 - Blue Flash
    # CC/33AE - Blue Flash
    # CC/45A9 - White Flash
    # CC/45AC - White Flash
    # CC/45AF - White Flash
    # CC/462D - White Flash
    # CC/4630 - White Flash
    # CC/4633 - White Flash
    # CC/4636 - White Flash
    # CC/4639 - White Flash
    # CC/464E - White Flash
    # CC/4690 - White Flash
    # CC/4693 - White Flash
    # CC/4696 - White Flash
    # CC/46F8 - White Flash
    # CC/477E - White Flash
    # CC/4CAE - White Flash
    # CC/5848 - White Flash
    # CC/5863 - White Flash
    # CC/5868 - White Flash
    # CC/59EC - White Flash
    # CC/59F5 - White Flash
    # CC/5C95 - Blue Flash
    # CC/793F - Red Flash
    # CC/7955 - Red Flash
    # CC/79A8 - White Flash
    # CC/79B4 - White Flash
    # CC/79D2 - White Flash
    # CC/79E2 - White Flash
    # CC/7A89 - Blue Flash
    # CC/7BD4 - Blue Flash
    # CC/7BD7 - Blue Flash
    # CC/7C4C - Blue Flash
    # CC/7D8B - Red Flash
    # CC/7DAC - Red Flash
    # CC/7DDF - Red Flash
    # CC/7E2A - Blue Flash
    # CC/80FD - Red Flash
    # CC/8329 - Red Flash
    # CC/8750 - Red Flash
    # CC/875D - Blue Flash
    # CC/876A - Green Flash
    # CC/87C7 - Red Flash
    # CC/87D4 - Blue Flash
    # CC/87E1 - Green Flash
    # CC/881A - Red Flash
    # CC/8827 - Blue Flash
    # CC/8834 - Green Flash
    # CC/887D - Red Flash
    # CC/888A - Blue Flash
    # CC/8897 - Green Flash
    # CC/8A66 - Red Flash
    # CC/8A73 - Blue Flash
    # CC/8A80 - Green Flash
    # CC/93C3 - Blue Flash
    # CC/93CC - End Color Effects
    # CC/9434 - Blue Flash
    # CC/94EC - End Color Effects
    # CC/9AF9 - Blue Flash
    # CC/9B03 - Blue Flash
    # CC/9FE3 - End Color Effects
    # CC/A483 - Red Flash
    # CC/BDDD - White Flash
    # CC/BE36 - White Flash
    # CC/BE7F - White Flash
    # CC/C58F - Blue Flash
    # CC/D6FB - Blue Flash
    # CC/D713 - Blue Flash
    # CC/D720 - Blue Flash


def vanish_doom(output_rom_buffer: BytesIO):
    jm_write_patch(output_rom_buffer, 'patch_vanish_doom.txt')


def stacking_immunities(output_rom_buffer: BytesIO):
    jm_write_patch(output_rom_buffer, 'patch_stacking_immunities_fix.txt')


def mp_color_digits(output_rom_buffer: BytesIO):
    jm_write_patch(output_rom_buffer, 'patch_mp_color_digits.txt')


def can_always_access_esper_menu(output_rom_buffer: BytesIO):
    jm_write_patch(output_rom_buffer, 'patch_can_always_access_esper_menu.txt')


def alphabetized_lores(output_rom_buffer: BytesIO):
    jm_write_patch(output_rom_buffer, 'patch_alphabetized_lores.txt')


def description_disruption(output_rom_buffer: BytesIO):
    jm_write_patch(output_rom_buffer, 'patch_description_disruption.txt')


def informative_miss(output_rom_buffer: BytesIO):
    jm_write_patch(output_rom_buffer, 'patch_informative_miss.txt')


def improved_equipment_menus(output_rom_buffer: BytesIO):
    jm_write_patch(output_rom_buffer, 'patch_improved_equip_menu.txt')
    jm_write_patch(output_rom_buffer, 'patch_improved_shop_menu.txt')


def verify_randomtools_patches(output_rom_buffer: BytesIO):
    rt_verify_patches(output_rom_buffer, strict=True)

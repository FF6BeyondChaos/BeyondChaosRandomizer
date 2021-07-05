from utils import Substitution


def allergic_dog(fout):
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
    allergic_dog_sub.write(fout)


# Moves check for dead banon after Life 3 so he doesn't revive and then game over.
def banon_life3(fout):
    banon_sub = Substitution()
    banon_sub.set_location(0x206bf)
    banon_sub.bytestring = [
        0x89, 0xC2,        # BIT #$C2       (Check for Dead, Zombie, or Petrify status)
        #06C1
        0xF0, 0x09,        # BEQ $06CC      (branch if none set)
        #06C3
        0xBD, 0x19, 0x30,  # LDA $3019,X
        #06C6
        0x0C, 0x3A, 0x3A,  # TSB $3A3A      (add to bitfield of dead-ish or escaped monsters)
        #06C9
        0x20, 0xC8, 0x07,  # JSR $07C8      (Clear Zinger, Love Token, and Charm bonds, and
                           #                 clear applicable Quick variables)
        #06CC
        0xBD, 0xE4, 0x3E,  # LDA $3EE4,X
        #06CF
        0x10, 0x2F,        # BPL $0700      (Branch if alive)
        #06D1
        0x20, 0x10, 0x07,  # JSR $0710   (If Wound status set on mid-Jump entity, replace
                           #              it with Air Anchor effect so they can land first)
        #06D4
        0xBD, 0xE4, 0x3E, # LDA $3EE4,X
        #06D7
        0x89, 0x02,       # BIT #$02
        #06D9
        0xF0, 0x03,       # BEQ $06DE      (branch if no Zombie Status)
        #06DB
        0x20, 0x28, 0x07, # JSR $0728      (clear Wound status, and some other bit)
        #06DE
        0xBD, 0xE4, 0x3E, # LDA $3EE4,X
        #06E1
        0x10, 0x1D,       # BPL $0700      (Branch if alive)
        #06E3
        0xBD, 0xF9, 0x3E, # LDA $3EF9,X
        #06E6
        0x89, 0x04,       # BIT #$04
        #06E8
        0xF0, 0x05,       # BEQ $06EF      (branch if no Life 3 status)
        #06EA
        0x20, 0x99, 0x07, # JSR $0799      (prepare Life 3 revival)
        #06ED
        0x80, 0x11,       # BRA $0700
        #06EF
        0xE0, 0x08,       # CPX #$08
        #06F1
        0xB0, 0x0C,       # BCS $06E4      (branch if monster)
        #06F3
        0xBD, 0xD8, 0x3E, # LDA $3ED8,X    (Which character)
        #06F6
        0xC9, 0x0E,       # CMP #$0E
        #06F8
        0xD0, 0x06,       # BNE $0700      (Branch if not Banon)
        #06FA
        0xA9, 0x06,       # LDA #$06
        #06FC
        0x8D, 0x6E, 0x3A, # STA $3A6E      (Banon fell... "End of combat" method #6)
        #06FF
        0xEA,
    ]
    banon_sub.write(fout)


def vanish_doom(fout):
    vanish_doom_sub = Substitution()
    vanish_doom_sub.bytestring = bytes([
        0xAD, 0xA2, 0x11, 0x89, 0x02, 0xF0, 0x07, 0xB9, 0xA1, 0x3A, 0x89, 0x04,
        0xD0, 0x6E, 0xA5, 0xB3, 0x10, 0x1C, 0xB9, 0xE4, 0x3E, 0x89, 0x10, 0xF0,
        0x15, 0xAD, 0xA4, 0x11, 0x0A, 0x30, 0x07, 0xAD, 0xA2, 0x11, 0x4A, 0x4C,
        0xB3, 0x22, 0xB9, 0xFC, 0x3D, 0x09, 0x10, 0x99, 0xFC, 0x3D, 0xAD, 0xA3,
        0x11, 0x89, 0x02, 0xD0, 0x0F, 0xB9, 0xF8, 0x3E, 0x10, 0x0A, 0xC2, 0x20,
        0xB9, 0x18, 0x30, 0x04, 0xA6, 0x4C, 0xE5, 0x22
        ])
    vanish_doom_sub.set_location(0x22215)
    vanish_doom_sub.write(fout)


def evade_mblock(fout):
    evade_mblock_sub = Substitution()
    evade_mblock_sub.bytestring = bytes([
        0xF0, 0x17, 0x20, 0x5A, 0x4B, 0xC9, 0x40, 0xB0, 0x9C, 0xB9, 0xFD, 0x3D,
        0x09, 0x04, 0x99, 0xFD, 0x3D, 0x80, 0x92, 0xB9, 0x55, 0x3B, 0x48,
        0x80, 0x43, 0xB9, 0x54, 0x3B, 0x48, 0xEA
        ])
    evade_mblock_sub.set_location(0x2232C)
    evade_mblock_sub.write(fout)


def death_abuse(fout):
    death_abuse_sub = Substitution()
    death_abuse_sub.bytestring = bytes([0x60])
    death_abuse_sub.set_location(0xC515)
    death_abuse_sub.write(fout)


def no_kutan_skip(fout):
    no_kutan_skip_sub = Substitution()
    no_kutan_skip_sub.set_location(0xAEBC2)
    no_kutan_skip_sub.bytestring = bytes([0x27, 0x01])
    no_kutan_skip_sub.write(fout)


def show_coliseum_rewards(fout):
    rewards_sub = Substitution()
    rewards_sub.set_location(0x37FD0)
    rewards_sub.bytestring = bytes([
        0x4C, 0x00, 0xF9
    ])
    rewards_sub.write(fout)

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
    rewards_sub.write(fout)

def informative_miss(fout):
    info_miss_sub = Substitution()
    info_miss_sub.set_location(0x026470) #$C26470 (End: $C26801)
#!C2Space    = $C26470
#!C2SpaceEnd = $C26801

#!miss = $3A5A ; miss targets
#!msgs = $3F52 ; 2 bytes before "null" bytes (for offset)
#!null = $3F54 ; immune targets
#!fail = $3F56 ; failed targets
#!bck1 = $EA   ; backup $11AA statuses
#!bck2 = $EC   ; backup $11AA statuses

    
    info_miss_sub.bytestring = bytes([
        #ClearMiss:
        0x9C, 0x3A, 0x5A,   #  STZ !miss
        0x9C, 0x3F, 0x56,   #  STZ !fail
        0x9C, 0x3F, 0x54,   #  STZ !null
        0x60,               #  RTS
        #StatusHelp:        ; (10 bytes)
        0xA5, 0xFC,         #  LDA $FC           status to set (1-2)
        0x05, 0xF4,         #  ORA $F4           status to clear (1-2)
        0x85, 0xE8,         #  STA $E8           store for now
        0x39, 0x33, 0x1C,   #  AND $331C,Y       are any vulnerable?
        0x60,               #  RTS
        #BackUpAttack:      ; (22 bytes)
        0xC2, 0x20,         #  REP #$20         ; 16-bit A
        0x20, 0x44, 0xFF,   #  JSR $44FF        ; zero statuses to set/clear
        0xAD, 0x11, 0xAA,   #  LDA $11AA        ; attack statuses 1-2
        0x85, 0xEA,         #  STA !bck1        ; save backup
        0xAD, 0x11, 0xAC,   #  LDA $11AC        ; attack statuses 3-4
        0x85, 0xEC,         #  STA !bck2        ; save backup
        0x9C, 0x11, 0xAA,   #  STZ $11AA        ; clear statuses 1-2
        0x9C, 0x11, 0xAC,   #  STZ $11AC        ; clear statuses 3-4
        0x60,               #  RTS
        #RestoreAttack:     ; (14 bytes)
        0x20, 0x44, 0x06,   #  JSR $4406        ; re-run status setting routine
        0xA5, 0xEA,         #  LDA !bck1        ; get backup statuses
        0x8D, 0x11, 0xAA,   #  STA $11AA        ; restore statuses 1-2
        0xA5, 0xEC,         #  LDA !bck2        ; get backup statuses
        0x8D, 0x11, 0xAC,   #  STA $11AC        ; restore statuses 3-4
        0x60,               #  RTS 
        #DeathNull:
        0xB9, 0x3A, 0xA1,   #  LDA $3AA1,Y     ; check immune to instant death bit
        0x80, ????          ##  BRA BitSet
        #SuplexNull:
        0xB9, 0x3A, 0xA1,   #  LDA $3C80,Y     ; check fractional dmg immunity bit
        #BitSet:
        0x24, 0x04,         #  BIT #$04        ; immune to instant death (or fractional)
        0xF0, ????          ##  BEQ SetEnd      ; if not immune, exit
        #SetNull:
        0x08,               #  PHP             ; save M, Z flags
        0xC2, 0x20,         #  REP #$20        ; 16-bit A
        0xB9, 0x30, 0x18,   #  LDA $3018,Y     ; get unique bit for target
        0x0C, 0x3F, 0x54,   ##  TSB !null       ; set null miss bit
        0x28,               #  PLP             ; restore 8-bit A, no zero flag
        #SetEnd:
        0x60               #  RTS
    ])








#StunFail:
#  STA $3DE8,Y       ; displaced vanilla code
#  BRA SetFailBit
#StamFail:
#  LDA $3B40,Y       ; stamina
#  CMP $EE           ; compare to random(128)
#  BCC FailExit      ; exit if hits
#SetFailBit:
#  PHP               ; store flags
#  REP #$20          ; 16-bit A
#  LDA $3018,Y       ; unique bitmask
#  TSB !fail         ; set "Fail" for target
#  PLP               ; restore flags
#FailExit:
#  RTS

#MissType:
#  CLC               ; default to no "miss" text
#  LDX #$04          ; point to "fail" bytes first
#.loop
#  BIT !msgs,X       ; is this miss message flagged
#  BNE .done         ; exit with X offset if so
#  DEX #2            ; point to next lowest message
#  BNE .loop
#.done
#  TRB !miss         ; test and reset miss flag
#  BNE .set_msg      ; if set, convert X to message value
#  DEX               ; else check if "null" or "fail" was set
#  BMI .exit         ; if not, exit
#  TSB !miss         ; else, show fail/null on next loop
#.exit
#  RTS 
#.set_msg
#  TRB !fail         ; clear "fail" bit
#  TRB !null         ; clear "null" bit
#  SEC               ; indicate "miss" text
#  TXA               ; get message flag in A
#  XBA               ; move to hi byte
#  RTS

#FinishMiss:
#  LDA !miss         ; any misses left
#  BEQ .continue     ; exit if not
#  JMP $62F3         ; else, loop again to handle null/fail
#.continue
#  PLY
#  PLX
#  RTS
    

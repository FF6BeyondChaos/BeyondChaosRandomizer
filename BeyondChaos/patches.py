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
    
def cycle_statuses(fout):
    cycles_sub = Substitution()
    cycles_sub.set_location(0x012E4F) #C12E4F
    cycles_sub.bytestring = bytes([0x80, 0x2B])         #BRA $2E7C	    (+43)
    cycles_sub.write(fout)

    cycles_sub.set_location(0x012E5C) #C12E5C
    cycles_sub.bytestring = bytes([0x80, 0x1E])         #BRA $2E7C	    (+30)
    cycles_sub.write(fout)

    cycles_sub.set_location(0x012E69) #C12E69
    cycles_sub.bytestring = bytes([
        0x80, 0x11,             #2E69                   BRA $2E7C	    (+17)
        #Status checker for outline colours.
        0xB9, 0xA9, 0x2E,       #2E6B/2E6C/2E6D         LDA $2EA9,Y     get current outline in rotation
        0x24, 0x38,             #2E6E/2E6F              BIT $38         check against current status
        0xD0, 0x10,             #2E70/2E71              BNE set_color   (+16) branch if a match was found 0x012E82
        0x4A,                   #2E72                   LSR A           check next status
        0x69, 0x00,             #2E73/2E74              ADC #$00        maintain wait bit
        0x99, 0xA9, 0x2E,       #2E75/2E76/2E77         STA $2EA9,Y     update outline colour rotation
        0xC9, 0x04,             #2E78/2E79              CMP #$20        loop over 6 statuses
        0xB0, 0xF2,             #2E7A/2E7B              BCS $2E6E       (-14)
        0xA9, 0x80,             #2E7C/2E7D              LDA #$80        no match found, reset to Rflect
        0x99, 0xA9, 0x2E,       #2E7E/2E7F/2E80         STA $2EA9,Y
        0x60,                   #2E81       RTS
        #set_colour
        0x29, 0xFC,             #2E82/2E83              AND #$FC        clear wait bit
        0x20, 0x0F, 0x1A,       #2E84/2E85/2E86         JSR $1A0F
        0xBF, 0x8B, 0x2E, 0xC1, #2E87/2E88/2E89/2E8A    LDA.l           outline_color_table,X  ; get outline colour
        #outline_color_table
        0x80, 0x36,             #2D8B/2E8C              BRA $2EC3	    (+54) Implement outline colour
        0x04,                   #2E8D                   DB $04          Slow
        0x03,                   #2E8E                   DB $03          Haste
        0x07,                   #2E8F                   DB $07          Stop
        0x02,                   #2E90                   DB $02          Shell
        0x01,                   #2E91                   DB $01          Safe
        0x00,                   #2E92                   DB $00          Rflect
        0xB9, 0xA9, 0x2E,       #2E93/2E94/2E95         LDA $2EA9,Y     current outline color rotation
        0x4A,                   #2E96                   LSR A           move one step forward
        0xB0, 0xE3,             #2E97/2E98              BCS             reset_rotation (-29) if wait bit set, clear it, reset and exit
        0x29, 0xFC,             #2E99/2E9A              AND $FC         keep 6 bits
        0xF0, 0xDF,             #2E9B/2E9C              BEQ             reset_rotation (-11) if all clear, reset and exit
        0x24, 0x38,             #2E9D/2E9E              BIT             $38 - check current status
        0xF0, 0xF5,             #2E9F/2EA0              BEQ             rotation_loop (-11) loop until match found
        0x80, 0xDB,             #2EA1/2EA2              BRA             update_rotation (-37) update outline rotation 0x012E7E
        0xEA, 0xEA, 0xEA, 0xEA, #2EA3/2EA4/2EA5/2EA6    NOP
        0xEA, 0xEA, 0xEA, 0xEA, #2EA7/2EA8/2EA9/2EAA    NOP
        0xEA, 0xEA, 0xEA, 0xEA, #2EAB/2EAC/2EAD/2EAE    NOP
        0xEA, 0xEA, 0xEA, 0xEA, #2EAF/2EB0/2EB1/2EB2    NOP
        0xEA                    #2EB3                   NOP
    ])
    cycles_sub.write(fout)
    
    cycles_sub.set_location(0x012ECF) #C12ECF
    cycles_sub.bytestring = bytes([
        #outline_control
        0xBF, 0xAA, 0xE3, 0xC2, #2ECF/2ED0/2ED1/2ED2    LDA $C2E3AA,X	Get colour change offset
        0x18,                   #2ED3                   CLC
        0x65, 0x2C,             #2ED4/2ED5              ADC $2C		    Add to current fade
        0x85, 0x36,             #2ED6/2ED7              STA $36		    Save here
        0x29, 0x3C,             #2ED8/2ED9              AND #$3C	    Isolate fade
        0x4A,                   #2EDA                   LSR A
        0x85, 0x2C,             #2EDB/2EDC              STA $2C		    Update fade
        0x64, 0x2D,             #2EDD/2EDE              STZ $2D
        0xA5, 0x36,             #2EDF                   LDA $36
        0x0A, 0x0A,             #2EE1/2EE2              ASL x2		    Is fade decreasing?
        0x90, 0x06,             #2EE3/2EE4              BCC $2EEB	    (+6) If so...
        0xA9, 0x1F,             #2EE5/2EE6              LDA #$1F	    ...subtract from 31
        0xE5, 0x2C,             #2EE7/2EE8              SBC $2C
        0x85, 0x2C,             #2EE9/2EEA              STA $2C
        0xA5, 0x2C,             #2EEB/2EEC              LDA $2C		    Get fade amount
        0xC9, 0x1F,             #2EED/2EEE              CMP #$1F	    Is it fully faded?
        0xD0, 0x06,             #2EEF/2EF0              BNE $2EF7       (+6) If so...
        0x20, 0x93, 0x2E,       #2EF1/2EF2              JSR $2E93       ...rotate colour
        0x80, 0x01,             #2EF3/2EF4              BRA $2EF7	    (+1)
        0xEA                    #2EF5                   NOP
    ])
    cycles_sub.write(fout)

    cycles_sub.set_location(0x02307D) #C2307D
    cycles_sub.bytestring = bytes([
        0xDA,                   #307D                   PHX			    Save party member index
        0xA5, 0xFE,             #307E/307F              LDA $FE		    Get row
        0x9D, 0xA1, 0x3A,       #3080/3081/3082         STA $3AA1,X	    Save to special props
        0xBD, 0xD9, 0x3E,       #3083/3084/3085         LDA $3ED9,X	    Preserve special sprite
        0x48,                   #3086                   PHA
        0xA3, 0x05,             #3087/3088              LDA $05,S		Get loop variable
        0x9D, 0xD9, 0x3E,       #3089/308A/308B         STA $3ED9,X	    Save to roster position
        0x7B,                   #308C                   TDC
        0x8A,                   #308D                   TXA
        0x0A, 0x0A, 0x0A, 0x0A, #308E/308F/3090/3091    ASL x4
        0xAA,                   #3092                   TAX
        0xA9, 0x06,             #3093/3094              LDA #$06
        0x85, 0xFE,             #3095/3096              STA $FE
        0x5A,                   #3097                   PHY			    Preserve Y-loop index
        0xB9, 0x01, 0x16,       #3098/3099/309A         LDA $1601,Y	    Get normal sprite & name
        0x9D, 0xAE, 0x2E,       #309B/309C/309D         STA $2EAE,X	    Store to display vars
        0xE8,                   #309E                   INX
        0xC8,                   #309F                   INY
        0xC6, 0xFE,             #30A0/30A1              DEC $FE		    7 iterations to loop
        0x10, 0xF4,             #30A2/30A3              BPL $3098	    (-12)
        0x7A,                   #30A4                   PLY			    Restore Y-loop index
        0x68,                   #30A5                   PLA			    Restore special sprite
        0xC9, 0xFF,             #30A6/30A7              CMP #$FF		Is it null?
        0xF0, 0x03,             #30A8/30A9              BEQ $30AD	    (+3) If not...
        0x9D, 0xA7, 0x2E,       #30AA/30AB              STA $2EA7,X	    ...overwrite sprite
        0xA9, 0x81,             #30AC/30AD              LDA #$81		Reflect + wait bit
        0x9D, 0xA2, 0x2E,       #30AE/30AF/30B0         STA $2EA2,X	    Init outline rotation
        0xA3, 0x03,             #30B1/30B2              LDA $03,S		Get character ID
        0x9D, 0xBF, 0x2E,       #30B3/30B4/30B5         STA $2EBF,X	    Save it
        0xC9, 0x0E,             #30B6/30B7              CMP #$0E		Banon or higher?
        0xC2, 0x20,             #30B8/30B9              REP #$20		16-bit A
        0xAA                    #30BA                   TAX			    Move to X
    ]) 
    cycles_sub.write(fout)
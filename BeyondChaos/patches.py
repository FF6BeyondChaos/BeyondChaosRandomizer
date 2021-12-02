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

def no_dance_stumbles(fout):
    nds_sub = Substitution()
    nds_sub.set_location(0x0217A0) #C217A0
    nds_sub.bytestring = bytes([0xEA, 0xEA])            #No Op x2
    nds_sub.write(fout)

def fewer_flashes(fout):
    anti_seizure_sub = Substitution()

    # ------------- Attack Animations -------------
    #
    # Removing Final Kefka Death Flashing
    #
    anti_seizure_sub.set_location(0x10023B)  # D0023B
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x100241)  # D00241
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x100249)  # D00249
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10024F)  # D0024F
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing Boss Death Flashing
    #
    anti_seizure_sub.set_location(0x100477)  # D00477
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10047D)  # D0047D
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x100485)  # D00485
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x100498)  # D00498
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing Magicite Transformation Flash
    #
    anti_seizure_sub.set_location(0x100F31)  # D00F31
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x100F40)  # D00F40
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing Ice 3 Flash
    #
    anti_seizure_sub.set_location(0x101979)  # D01979
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10197C)  # D0197C
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10197F)  # D0197F
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x101982)  # D01982
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x101985)  # D01985
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x101988)  # D01988
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10198B)  # D0198B
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10198E)  # D0198E
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x101991)  # D01991
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing Fire 3 Flash
    #
    anti_seizure_sub.set_location(0x1019FB)  # D019FB
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x101A1D)  # D01A1D
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing Phantasm Flash
    #
    anti_seizure_sub.set_location(0x101E08)  # D01E08
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x101E0E)  # D01E0E
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x101E20)  # D01E20
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x101E28)  # D01E28
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing Tiger Break Flash
    #
    anti_seizure_sub.set_location(0x10240E)  # D0240E
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x102412)  # D02412
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x102416)  # D02416
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing Diffuser Flash
    #
    anti_seizure_sub.set_location(0x103AEB)  # D03AEB
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x103AEE)  # D03AEE
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x103AF1)  # D03AF1
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x103AF4)  # D03AF4
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x103AF7)  # D03AF7
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x103AFA)  # D03AFA
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x103AFD)  # D03AFD
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x103B00)  # D03B00
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x103B03)  # D03B00
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing Cat Rain Flash
    #
    anti_seizure_sub.set_location(0x102678)  # D02678
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10267C)  # D0267C
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing Unknown Script 1's Flash
    #
    anti_seizure_sub.set_location(0x1026EF)  # D026EF
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1026FB)  # D026FB
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing Mirager Flash
    #
    anti_seizure_sub.set_location(0x102792)  # D02792
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x102796)  # D02796
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing Sabre Soul Flash
    #
    anti_seizure_sub.set_location(0x1027D4)  # D027D4
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1027DB)  # D027DB
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing Back Blade Flash
    #
    anti_seizure_sub.set_location(0x1028D4)  # D028D4
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1028E0)  # D028E0
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing Royal Shock Flash
    #
    anti_seizure_sub.set_location(0x102968)  # D02968
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10299C)  # D0299C
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x102974)  # D02974
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing Unknown Script 2's Flash
    #
    anti_seizure_sub.set_location(0x102AAE)  # D02AAE
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x102AB2)  # D02AB2
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing Absolute Zero Flash
    #
    anti_seizure_sub.set_location(0x102BFF)  # D02BFF
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x102C03)  # D02C03
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing Unknown Script 3's Flash
    #
    anti_seizure_sub.set_location(0x1030CB)  # D030CB
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1030CF)  # D030CF
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing Reverse Polarity Flash
    #
    anti_seizure_sub.set_location(0x10328C)  # D0328C
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x103293)  # D03293
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing Rippler Flash
    #
    anti_seizure_sub.set_location(0x1033C7)  # D033C7
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1033CB)  # D033CB
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing Step Mine Flash
    #
    anti_seizure_sub.set_location(0x1034DA)  # D034DA
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1034E1)  # D034E1
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing Unknown Script 4's Flash
    #
    anti_seizure_sub.set_location(0x1035E7)  # D035E7
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1035F7)  # D035F7
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing Schiller Flash
    #
    anti_seizure_sub.set_location(0x10380B)
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    # This commented out code is for vanilla Schiller, which BC is no longer using
    # anti_seizure_sub.set_location(0x10381A)  # D0381A
    # anti_seizure_sub.bytestring = bytes([0xE0])
    # anti_seizure_sub.write(fout)

    # anti_seizure_sub.set_location(0x10381E)  # D0381E
    # anti_seizure_sub.bytestring = bytes([0xF0])
    # anti_seizure_sub.write(fout)

    #
    # Removing Wall Change Flash
    #
    anti_seizure_sub.set_location(0x10399F)  # D0399F
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1039A4)  # D039A4
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1039AA)  # D039AA
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1039B0)  # D039B0
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1039B6)  # D039B6
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1039BC)  # D039BC
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1039C2)  # D039C2
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1039C8)  # D039C8
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1039CE)  # D039CE
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1039D5)  # D039D5
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing Ultima Flash
    #
    anti_seizure_sub.set_location(0x1056EE)  # D056EE
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1056F6)  # D056F6
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing Bolt 3/Giga Volt Flash
    #
    anti_seizure_sub.set_location(0x10588F)  # D0588F
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x105894)  # D05894
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x105897)  # D05897
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10589A)  # D0589A
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10589D)  # D0589D
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1058A2)  # D058A2
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1058A7)  # D058A7
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1058AC)  # D058AC
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1058B1)  # D058B1
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing X-Zone Flash
    #
    anti_seizure_sub.set_location(0x105A5E)  # D05A5E
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x105A6B)  # D05A6B
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x105A78)  # D05A78
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing Dispel Flash
    #
    anti_seizure_sub.set_location(0x105DC3)  # D05DC3
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x105DCA)  # D05DCA
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x105DD3)  # D05DD3
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x105DDC)  # D05DDC
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x105DE5)  # D05DE5
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x105DEE)  # D05DEE
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing Pep Up/Break Flash
    #
    anti_seizure_sub.set_location(0x1060EB)  # D060EB
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1060EF)  # D060EF
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing Shock Flash
    #
    anti_seizure_sub.set_location(0x1068BF)  # D068BF
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1068D1)  # D068D1
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing Bum Rush Flashes
    #
    # Flash 1
    anti_seizure_sub.set_location(0x106C7F)  # D06C7F
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x106C88)  # D06C88
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    # Flash 2
    anti_seizure_sub.set_location(0x106C96)  # D06C96
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x106C9F)  # D06C9F
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    # Other Bum Rush Background Sets - possibly unnecessary
    anti_seizure_sub.set_location(0x106C3F)  # D06C3F
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x106C48)  # D06C48
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x106C54)  # D06C54
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x106C88)  # D06C87
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    #
    # Removing Quadra Slam/Slice Flash
    #
    # White Flash
    anti_seizure_sub.set_location(0x1073DD)  # D073DD
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1073EF)  # D073EF
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1073F4)  # D073F4
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    # Green Flash
    anti_seizure_sub.set_location(0x107403)  # D07403
    anti_seizure_sub.bytestring = bytes([0x40])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x107425)  # D07425
    anti_seizure_sub.bytestring = bytes([0x50])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10742A)  # D0742A
    anti_seizure_sub.bytestring = bytes([0x50])
    anti_seizure_sub.write(fout)

    # Blue Flash
    anti_seizure_sub.set_location(0x107437)  # D07437
    anti_seizure_sub.bytestring = bytes([0x20])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x107459)  # D07459
    anti_seizure_sub.bytestring = bytes([0x30])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10745E)  # D0745E
    anti_seizure_sub.bytestring = bytes([0x30])
    anti_seizure_sub.write(fout)

    # Red Flash
    anti_seizure_sub.set_location(0x107491)  # D07491
    anti_seizure_sub.bytestring = bytes([0x80])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1074B3)  # D074B3
    anti_seizure_sub.bytestring = bytes([0x90])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1074B8)  # D074B8
    anti_seizure_sub.bytestring = bytes([0x90])
    anti_seizure_sub.write(fout)

    #
    # Removing Slash Flash
    #
    anti_seizure_sub.set_location(0x1074F5)  # D074F5
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1074FE)  # D074FE
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x1074F8)  # D074F8
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Removing Flash Flash
    #
    anti_seizure_sub.set_location(0x107851)  # D07851
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10785D)  # D0785D
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    # ------------- Battle Event Scripts -------------
    #
    # Battle Event Script $15
    #
    anti_seizure_sub.set_location(0x10B887)  # D0B887
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10B88D)  # D0B88D
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10B894)  # D0B894
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10B89A)  # D0B89A
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10B8A1)  # D0B8A1
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10B8A7)  # D0B8A7
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10B8AE)  # D0B8AE
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10B8B4)  # D0B8B4
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10BCF5)  # D0BCF5
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10BCF9)  # D0BCF9
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    #
    # Battle Event Script $19
    #
    anti_seizure_sub.set_location(0x10C7A4)  # D0C7A4
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10C7AA)  # D0C7AA
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10C7B1)  # D0C7B1
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10C7B7)  # D0C7B7
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10C7BE)  # D0C7BE
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10C7C4)  # D0C7C4
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10C7CB)  # D0C7CB
    anti_seizure_sub.bytestring = bytes([0xE0])
    anti_seizure_sub.write(fout)

    anti_seizure_sub.set_location(0x10C7D1)  # D0C7D1
    anti_seizure_sub.bytestring = bytes([0xF0])
    anti_seizure_sub.write(fout)

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

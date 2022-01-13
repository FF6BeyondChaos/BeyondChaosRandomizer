import tkinter, os
from tkinter import ttk
from tkinter import messagebox
from remonsterate.remonsterate import remonsterate, VERSION
from sys import argv, stdout
from traceback import format_exc
from time import time, sleep

class RemonstrateGUI(tkinter.Frame):
    def __init__(self, master):
        tkinter.Frame.__init__(self)
        self.master = master
        self.rom_widget = None
        self.seed_widget = None
        self.image_widget = None
        self.monster_widget = None
        self.rom_files = []
        self.txt_files = []
        self.image_files = []
        self.monster_files = []
        self.font = 'Arial'
        self.font_size = 12

        # Populate the file name lists. Iterates through directories starting
        #   at the directory containing the exe file. Does not traverse
        #   directories past the depth specified by walk_distance.
        walk_distance = 2
        exe_directory = os.path.abspath(".")
        exe_directory_level = exe_directory.count(os.path.sep)
        for root, dirs, files in os.walk("."):
            current_walking_directory = os.path.abspath(root)
            current_directory_level = current_walking_directory.count(
                os.path.sep)
            if current_directory_level > exe_directory_level + walk_distance:
                # del dirs[:] empties the list that os.walk uses to determine
                #   what directories to walk through, meaning os.walk will move
                #   on to the next directory. It does NOT delete or modify
                #   files on the hard drive.
                del dirs[:]
            else:
                for filename in files:
                    filepath = os.path.join(root, filename)
                    f = filename.lower()
                    if f.endswith(".smc") or f.endswith(".sfc"):
                        self.rom_files.append(filepath)
                    elif f.endswith(".txt"):
                        self.txt_files.append(filepath)

        self.rom_files = sorted(set(self.rom_files), key=lambda f: f.lower())
        self.txt_files = sorted(
            set(self.txt_files),
            key=lambda f: (f.count(os.path.sep), f.lower()))
        self.image_files = [f for f in self.txt_files if 'images' in f.lower()]
        self.image_files += [f for f in self.txt_files
                             if f not in self.image_files]
        self.monster_files = [f for f in self.txt_files
                              if 'monsters' in f.lower()]
        self.monster_files += [f for f in self.txt_files
                               if f not in self.monster_files]

        widget = tkinter.Label(
            master=self.master,
            text='Make sure to back up your rom first!',
            font=(self.font, self.font_size)
            )
        widget.grid(row=0, column=0, columnspan=2,
                    padx=(10,10), pady=(10,0), sticky='w')

        # Row 1: ROM File Information
        widget = tkinter.Label(
            master=self.master,
            text='FF6 ROM',
            font=(self.font, self.font_size)
            )
        widget.grid(row=1, column=0, padx=(10,10), pady=(10,0), sticky='w')

        rom_widget = tkinter.ttk.Combobox(
            master = self.master,
            values = self.rom_files,
            font=(self.font, self.font_size)
            )
        rom_widget.grid(row=1, column=1, padx=(0,10), pady=(10,0), sticky='we')

        # Row 2: ROM type
        radioframe = tkinter.Frame(master=self.master)
        radio_var = tkinter.StringVar(self.master)
        radio_var.set('AUTO')
        radio_widget = tkinter.Radiobutton(
            master=radioframe, text='v1.0 (sketch glitch)',
            variable=radio_var, value='1.0')
        radio_widget.pack(side=tkinter.TOP, anchor=tkinter.W)
        radio_widget = tkinter.Radiobutton(
            master=radioframe, text='v1.1 (no sketch glitch)',
            variable=radio_var, value='1.1')
        radio_widget.pack(side=tkinter.TOP, anchor=tkinter.W)
        radio_widget = tkinter.Radiobutton(
            master=radioframe, text='Autodetect',
            variable=radio_var, value='AUTO')
        radio_widget.pack(side=tkinter.TOP, anchor=tkinter.W)
        radioframe.grid(row=2, column=1, padx=(0,10), pady=(10,0), sticky='w')

        # Row 3: Seed Information
        widget = tkinter.Label(
            master=self.master,
            text='Seed',
            font=(self.font, self.font_size)
            )
        widget.grid(row=3, column=0, padx=(10,10), pady=(10,0), sticky='w')

        seed_widget = tkinter.Text(
            master = self.master,
            height = 1,
            width = 10,
            font=(self.font, self.font_size)
            )
        seed_widget.grid(row=3, column=1, padx=(0,10), pady=(10,0),
                         sticky='we')

        # Row 4: Images File Information
        widget = tkinter.Label(
            master=self.master,
            text='Images File',
            font=(self.font, self.font_size)
            )
        widget.grid(row=4, column=0, padx=(10,10), pady=(10,0), sticky='w')

        image_widget = tkinter.ttk.Combobox(
            master = self.master,
            values = self.image_files,
            font=(self.font, self.font_size)
            )
        image_widget.grid(row=4, column=1, padx=(0,10), pady=(10,0),
                          sticky='we')

        # Row 5: Monsters File Information
        widget = tkinter.Label(
            master=self.master,
            text='Monsters File',
            font=(self.font, self.font_size)
            )
        widget.grid(row=5, column=0, padx=(10,10), pady=(10,0), sticky='w')

        monster_widget = tkinter.ttk.Combobox(
            master = self.master,
            values = self.monster_files,
            font=(self.font, self.font_size)
            )
        monster_widget.grid(row=5, column=1, padx=(0,10), pady=(10,0),
                            sticky='we')

        # Row 6: Generate Button
        # Button event
        def validate(event = None):
            validate = True
            error_text = 'Error:\n'
            current_rom = rom_widget.get()
            current_seed = seed_widget.get(1.0, 'end-1c')
            current_images = image_widget.get()
            current_monsters = monster_widget.get()

            # Validate selection of the ROM file
            if current_rom == '':
                validate = False
                error_text = error_text + 'You must select a FF6 ROM file. \n'

            # Validate input of the seed
            if current_seed == '':
                current_seed = time()
            else:
                # The generator can only handle integers.
                # Test if the seed is an integer.
                try:
                    int(current_seed)
                except ValueError:
                    # If the seed is not an integer, turn it into one
                    new_current_seed = []
                    for character in current_seed:
                        new_current_seed.append(ord(character))

                    # Multiply the ordinals together to get a seed
                    current_seed = 1
                    for number in new_current_seed:
                        current_seed *= number

            # Validate input of the image text file
            if current_images == '':
                validate = False
                error_text = error_text + 'You must select an image file. \n'

            # Validate input of the monsters text file
            if current_monsters == '':
                validate = False
                error_text = error_text + 'You must select a monsters file. \n'

            # If everything looked good, close the GUI and commence generation
            if validate:
                self.master.destroy()
                remonsterate(current_rom,
                             current_seed,
                             current_images,
                             current_monsters,
                             rom_type=radio_var.get())
                print('Finished successfully.')
            else:
                tkinter.messagebox.showerror('Missing Files', error_text)

        widget = tkinter.Button(
            master = self.master,
            text='Generate',
            command=lambda:validate(),
            font=(self.font, self.font_size)
            )
        widget.grid(row=6, column=0, columnspan=2, padx=(10,10), pady=(10,10),
                    sticky='we')



if __name__ == '__main__':
    root = None
    try:
        if len(argv) > 3:
            remonsterate(*argv[1:])
            print('Finished successfully.')
        else:
            print('Make sure to back up your rom first!')
            root = tkinter.Tk()
            GUI = RemonstrateGUI(root)
            root.columnconfigure(1, weight=1)
            root.title('Remonstrate v{0}'.format(VERSION))
            root.minsize(500, 185)
            root.mainloop()

    except Exception:
        print(format_exc())

    if root is None:
        input('Press Enter to close this program. ')
    else:
        stdout.write('Closing program in ')
        for i in range(5, 0, -1):
            stdout.write('%s ' % i)
            stdout.flush()
            sleep(1)
        stdout.write('\n')

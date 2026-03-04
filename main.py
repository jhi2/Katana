import tkinter as tk
from flaskwebgui import FlaskUI
from ui import app
from version import v, sl
print("""                                                                                                                 
                                                                                                                 
KKKKKKKKK    KKKKKKK                          tttt                                                               
K:::::::K    K:::::K                       ttt:::t                                                               
K:::::::K    K:::::K                       t:::::t                                                               
K:::::::K   K::::::K                       t:::::t                                                               
KK::::::K  K:::::KKK  aaaaaaaaaaaaa  ttttttt:::::ttttttt      aaaaaaaaaaaaa  nnnn  nnnnnnnn      aaaaaaaaaaaaa   
  K:::::K K:::::K     a::::::::::::a t:::::::::::::::::t      a::::::::::::a n:::nn::::::::nn    a::::::::::::a  
  K::::::K:::::K      aaaaaaaaa:::::at:::::::::::::::::t      aaaaaaaaa:::::an::::::::::::::nn   aaaaaaaaa:::::a 
  K:::::::::::K                a::::atttttt:::::::tttttt               a::::ann:::::::::::::::n           a::::a 
  K:::::::::::K         aaaaaaa:::::a      t:::::t              aaaaaaa:::::a  n:::::nnnn:::::n    aaaaaaa:::::a 
  K::::::K:::::K      aa::::::::::::a      t:::::t            aa::::::::::::a  n::::n    n::::n  aa::::::::::::a 
  K:::::K K:::::K    a::::aaaa::::::a      t:::::t           a::::aaaa::::::a  n::::n    n::::n a::::aaaa::::::a 
KK::::::K  K:::::KKKa::::a    a:::::a      t:::::t    tttttta::::a    a:::::a  n::::n    n::::na::::a    a:::::a 
K:::::::K   K::::::Ka::::a    a:::::a      t::::::tttt:::::ta::::a    a:::::a  n::::n    n::::na::::a    a:::::a 
K:::::::K    K:::::Ka:::::aaaa::::::a      tt::::::::::::::ta:::::aaaa::::::a  n::::n    n::::na:::::aaaa::::::a 
K:::::::K    K:::::K a::::::::::aa:::a       tt:::::::::::tt a::::::::::aa:::a n::::n    n::::n a::::::::::aa:::a
KKKKKKKKK    KKKKKKK  aaaaaaaaaa  aaaa         ttttttttttt    aaaaaaaaaa  aaaa nnnnnn    nnnnnn  aaaaaaaaaa  aaaa                                                                                                                                                                                                                                                                                                                            
""")
print("Development copy")
print("Distributed under the GNU AGPL 3.0 License")
print("Version: " + v)  
print("Credit to: SpiritDude for Print3R CLI tool")




def show_splash():
    print("INFO: Starting splash screen")
    splash_root = tk.Tk()
    splash_root.overrideredirect(True)
    
    width = 600
    height = 400
    
    screen_width = splash_root.winfo_screenwidth()
    screen_height = splash_root.winfo_screenheight()
    screen_x = 0
    screen_y = 0
    
    try:
        from screeninfo import get_monitors
        primary = next((m for m in get_monitors() if m.is_primary), get_monitors()[0])
        screen_width = primary.width
        screen_height = primary.height
        screen_x = primary.x
        screen_y = primary.y
    except Exception:
        if screen_width > 2560:
            screen_width = screen_width // 2

    try:
        from PIL import Image, ImageTk
        import os
        
        img_path = os.path.join(os.path.dirname(__file__), "splash.jpg")
        img = Image.open(img_path)
        
        # Scale down the image to a maximum reasonable size for a splash screen
        img.thumbnail((600, 400), Image.Resampling.LANCZOS)
        width = img.width
        height = img.height
            
        bg_image = ImageTk.PhotoImage(img)
        
        x = screen_x + (screen_width // 2) - (width // 2)
        y = screen_y + (screen_height // 2) - (height // 2)
        splash_root.geometry(f'{width}x{height}+{int(x)}+{int(y)}')
        
        # Create a container
        canvas = tk.Canvas(splash_root, width=width, height=height, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        canvas.create_image(0, 0, image=bg_image, anchor="nw")
        
        # Draw text over the image
        canvas.create_text(width // 2, height // 2, text=f"Katana:\n Print Awesome.\n Version {v}\n Powered by CuraEngine", font=("Helvetica", 36, "bold"), fill="white", justify="center")
        
        # Store reference
        splash_root.bg_image = bg_image
        
    except Exception as e:
        # Fallback if image fails
        print(f"Splash screen image error: {e}")
        x = screen_x + (screen_width // 2) - (width // 2)
        y = screen_y + (screen_height // 2) - (height // 2)
        splash_root.geometry(f'{width}x{height}+{int(x)}+{int(y)}')
        label = tk.Label(splash_root, text=f"Katana...\n Print Awesome...\n Version {v}\n Powered by CuraEngine", font=("Helvetica", 24))
        label.pack(expand=True)
    
    splash_root.after(sl, splash_root.destroy)
    splash_root.mainloop()
    print("INFO: Splash screen closed")

show_splash()
FlaskUI(server="flask", app=app, extra_flags=["--class=Katana"]).run()

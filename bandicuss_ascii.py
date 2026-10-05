"""Colored ASCII weather intro. Printable ASCII artwork, no blocks."""
import math
WIDTH, HEIGHT, FPS, DURATION = 78, 24, 16, 8.0
SCENES = ('FIRST LIGHT', 'STORM FRONT', 'SNOWFALL', 'AFTER DARK')
PALETTE = [(11,21,40),(95,120,147),(124,152,175),(166,195,206),(220,237,230),
           (255,214,150),(255,170,106),(217,134,132),(146,127,174),(89,174,184),
           (110,218,198),(176,232,225),(89,120,164),(115,157,208)]
LOGO = [
 r' ____     _    _   _ ____ ___ ____ _   _ ____ ____  ',
 r'| __ )   / \  | \ | |  _ \_ _/ ___| | | / ___/ ___| ',
 r'|  _ \  / _ \ |  \| | | | | | |   | | | \___ \___ \ ',
 r'| |_) |/ ___ \| |\  | |_| | | |___| |_| |___) |__) |',
 r'|____//_/   \_\_| \_|____/___\____|\___/|____/____/ ',
]
CLOUD=[r'     .--.       ',r'  .-(    ).     ',r' (___.__)__)    ']


class Frame:
    def __init__(self):self.cells=[[' ',1] for _ in range(WIDTH*HEIGHT)]
    def put(self,x,y,text,color=3):
        y=round(y);x=round(x)
        if not 0<=y<HEIGHT:return
        for i,ch in enumerate(text):
            if 0<=x+i<WIDTH and ch!=' ':self.cells[y*WIDTH+x+i]=[ch,color]
    def art(self,x,y,lines,color=3):
        for dy,line in enumerate(lines):self.put(x,y+dy,line,color)
    def dot(self,x,y,ch,c):self.put(x,y,ch,c)
    def pack(self):return bytes(n for ch,c in self.cells for n in (ord(ch),c))


def scene_frame(scene,t):
    f=Frame()
    if scene==0:
        f.art(3+round(t*2),2,CLOUD,7);f.art(24+round(t),5,CLOUD,3)
        rays = [r"    \  |  /",r"  `. .---. .'",r" -- (     ) --",r"  .' `---' `.",r"    /  |  \ "]
        f.art(54,1,rays,5)
        for i in range(3):f.put(44+i*5+t*2,4-i,"v" if int(t*4+i)%2 else "-v-",6)
        f.art(0,10,[r'     /\                 /\                         /\ ',
                    r'  __/  \__      /\    _/  \__          /\       __/  \___',
                    r'_/        \____/  \__/       \________/  \_____/         \___'],8)
        for y in range(13,17):
            f.put(0,y,'~ '*39,1)
            f.put(49+round(math.sin(y+t*2)*4),y,'~ ~  ~ ~',6 if y%2 else 7)
        f.art(3,12,[r'   /\ ',r'  /++\ ',r' /++++\ ',r'   ||'],9)
        f.art(68,11,[r'   /\ ',r'  /++\ ',r' /++++\ ',r'/++++++\ ',r'   ||'],9)
    elif scene==1:
        for x in [-3,22,48,67]:f.art(x-t*3,1,CLOUD,2)
        for x in [6,32,55]:f.art(x-t,3,CLOUD,12)
        for i in range(55):
            x=(i*19-int(t*16))%78;y=5+(i*7+int(t*13))%10
            f.dot(x,y,'/' if i%3 else "'",13 if i%2 else 2)
        if .75<t<1.15:f.art(52,5,[r' /',r'/__',r'  /',r' /',r'/'],5)
        for i in range(11):
            x=i*7;top=10-i*7%4
            f.put(x,top,'+----+',2)
            for y in range(top+1,16):
                f.put(x,y,'|    |',1)
                if (y+i)%2:f.put(x+2,y,':',5)
        for x in range(0,78,9):f.put(x+int(t*3)%5,16,'~--~',9)
    elif scene==2:
        f.art(52,1,[r'     .--.',r'   .(    ).',r'  (___/___)'],3)
        f.art(1,5,[r'                   /\ ',r'       /\         /  \            /\ ',
                    r'      /  \       / /\ \    /\    /  \ ',
                    r'  ___/^^^^\_____/ /  \ \__/  \__/^^^^\___',
                    r' /            / /    \      ^^^          \ ',
                    r'/            /        \                  \ '],3)
        for x,y in [(3,9),(12,10),(65,8),(70,11)]:
            f.art(x,y,[r'   *',r'  /+\ ',r' /+++\ ',r'/+++++\ ',r'   |'],9)
        f.art(43,11,[r'   /\ ',r'  /__\ ',r' /____\ ',r' |[] |',r'_|___|_'],2)
        f.put(45,14,'[]',5)
        for i in range(43):
            x=(i*23+t*2+math.sin(i+t))%78;y=(i*13+t*(2+i%3))%17
            f.dot(x,y,'*' if i%5==0 else '.',4 if i%3 else 13)
        f.put(0,16,'__..___..____..__..___..____..____..___..__..____..___..____..___..___..____',3)
    else:
        for i in range(34):
            x=(i*23+5)%78;y=(i*17+3)%10
            f.dot(x,y,'+' if (i+int(t*3))%7==0 else '.',3 if i%3 else 5)
        f.art(61,1,[r' .--.',r'(    `.',r' `.__.'],4)
        for x in range(2,76):
            y=5+math.sin(x*.13+t*.8)*2+math.sin(x*.28-t)*.6
            f.dot(x,y,'~',10)
            if x%2==0:f.dot(x,y+1,'|',9)
            if x%3==0:f.dot(x,y+2,':',8)
        f.art(0,11,[r'        /\                   /\                 /\ ',
                     r'   ____/  \____      /\_____/  \_____     _____/  \____',
                     r'__/            \____/               \___/             \___'],12)
        for x in [2,8,66,72]:f.art(x,12,[r'  ^',r' /|\ ',r'/|||\ ',r'  |'],9)
        f.put(22,15,'~  ~     ~     ~   ~     ~     ~  ~',1)
    # Keep the wordmark clear of scene details; only ASCII strokes draw it.
    for y,line in enumerate(LOGO):
        start=(WIDTH-len(line))//2
        for x in range(WIDTH):f.cells[(17+y)*WIDTH+x]=[' ',1]
        f.put(start,17+y,line,11 if y<2 else 9 if y<4 else 13)
    f.put(29,22,'ANY KEY TO CONTINUE',2)
    footer='W E A T H E R   C E N T E R'
    f.put((WIDTH-len(footer))//2,23,footer,3)
    return f.pack()


def frame_at(seconds):
    seconds=max(0,min(DURATION-1/FPS,seconds));scene=min(3,int(seconds/2))
    return scene_frame(scene,seconds-scene*2),scene


def ansi_frame(pixels,scene,columns=80,rows=24):
    from bandicuss_intro_layout import fit_canvas,resample,position,caption
    left,top,width,height=fit_canvas(columns,rows,WIDTH,22,captions=2)
    art=resample(pixels[:WIDTH*22*2],WIDTH,22,width,height,stride=2)
    lines=[]
    for y in range(height):
        lines.append(position(left,top+y));previous=None
        for x in range(width):
            i=(y*width+x)*2;char,c=art[i:i+2]
            if c!=previous:lines.append('\x1b[38;2;%d;%d;%dm'%PALETTE[c]);previous=c
            lines.append(chr(char))
        lines.append('\x1b[0m\x1b[K')
    lines.append(caption('W E A T H E R   C E N T E R',columns,top+height,(166,195,206)))
    lines.append(caption('ANY KEY TO CONTINUE',columns,top+height+1))
    return ''.join(lines)


def play_intro(duration=DURATION):
    import os,select,shutil,sys,termios,time,tty
    if not sys.stdin.isatty() or not sys.stdout.isatty():return
    if os.environ.get('NO_COLOR') is not None or os.environ.get('BANDICUSS_NO_ANIMATION'):return
    cols,rows=shutil.get_terminal_size()
    if cols<WIDTH+1 or rows<HEIGHT:return
    duration=max(.5,min(15,float(duration)));fd=sys.stdin.fileno();previous=termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd);sys.stdout.write('\x1b[?1049h\x1b[?25l\x1b[2J');sys.stdout.flush()
        start=time.monotonic();last_size=None
        while True:
            frame_start=time.monotonic();elapsed=frame_start-start
            if elapsed>=duration:break
            cols,rows=shutil.get_terminal_size()
            if cols<WIDTH+1 or rows<HEIGHT:break
            if (cols,rows)!=last_size:
                sys.stdout.write('\x1b[2J');last_size=(cols,rows)
            pixels,scene=frame_at(elapsed/duration*DURATION)
            sys.stdout.write(ansi_frame(pixels,scene,cols,rows));sys.stdout.flush()
            if select.select([sys.stdin],[],[],max(0,1/FPS-(time.monotonic()-frame_start)))[0]:os.read(fd,1);termios.tcflush(fd,termios.TCIFLUSH);break
    finally:
        try:
            termios.tcsetattr(fd,termios.TCSADRAIN,previous)
        finally:
            sys.stdout.write('\x1b[0m\x1b[?25h\x1b[?1049l');sys.stdout.flush()


if __name__=='__main__':play_intro()

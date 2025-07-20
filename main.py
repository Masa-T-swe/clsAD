# coding:utf-8
import time
import sys
import sqlite3

from termcolor import colored

import clsAD

cAD:clsAD
lap:list[float, float] = [0.0, 0.0]

def dbgprint(s: str):
    ''' デバッグプリント
            Args:
                s (str): 表示文字列
            Returns: 
            Note:
                import sys
                from termcolor import colored
                from termcolor import cprint
                表示を抑制する場合は以下の通り
                    > python -O scriptfile
                exm. cprint("dispstr","cyan", "on_white", attrs=["underline","strike"])

                avalable colors = [black|red|green|yellow|blue|magenta|cyan|white|
                    light_grey|dark_grey|light_red|light_green|light_yellow|light_blue|light_magenta|light_cyan]
                avalable on_colors = [on_black|on_red|on_green|on_yellow|on_blue|on_magenta|on_cyan|on_white|
                    on_light_grey|on_dark_grey|on_light_red|on_light_green|
                    on_light_yellow|on_light_blue|on_light_magenta|on_light_cyan]
                attrs=[bold|dark|underline|blink|reverse|concealed|strike]
    ''' 
    if __debug__:
        print(colored(s, "yellow"),file=sys.stderr)
        # cprint(s, "yellow")
        
def LapStart():
    ''' 時間計測開始関数
            Args: 
            Returns: 
            Note: 
                lap[]を使用する
    ''' 
    global lap
    lap[0] = time.time()
    
def LapStop() -> float:
    ''' 時間計測停止関数
            Args: 
            Returns: 
            Note: 
                lap[]を使用する
    ''' 
    global lap
    lap[1] = time.time()
    return lap[1] - lap[0]

def ADset(dbf):
    global cAD
    con = sqlite3.connect(dbf)
    with con:
        sql = "SELECT * FROM ADset ORDER BY ch"
        recs = con.execute(sql)
        c = 0
        for rec in recs:
            c += 1
            ch = rec[0]
            cAD.pCh[ch].pName = rec[1]
            cAD.pCh[ch].pRange = rec[2]
            cAD.pCh[ch].pMin = rec[3]
            cAD.pCh[ch].pMax = rec[4]
            cAD.pCh[ch].pOffset = rec[5]
            cAD.pCh[ch].pFormat = rec[6]
            cAD.pCh[ch].pUnit = rec[7]
        '''
        for i in range(c):
            dbgprint(cAD.pCh[i].pName)
            dbgprint(cAD.pCh[i].pRange)
            dbgprint(cAD.pCh[i].pMin)
            dbgprint(cAD.pCh[i].pMax)
            dbgprint(cAD.pCh[i].pOffset)
            dbgprint(cAD.pCh[i].pFormat)
            dbgprint(cAD.pCh[i].pUnit)
        '''
        
def main():
    global cAD
    cAD = clsAD.clsAD()
    ret = cAD.Open("AIO000")
    dbgprint(f"Open -> {cAD.pErrorStr}")
    dbgprint(f"{cAD.pName}:{cAD.pMaxChannel}")
    
    ADset("adtest.db")
    ret = cAD.SetRange()
    dbgprint(f"SetRange -> {cAD.pErrorStr}")

    key = ""
    while key.lower() != "q":
        key = input("Count? > ")
        if key.isdecimal():
            cnt = int(key)
            key = input("Channels? > ")
            if key.isdecimal():
                ch = int(key)
            
                # 非同期入力
                LapStart()
                dbgprint("Sampling Start")
                #cnt = 5000
                #ch = 32
                ret = cAD.Start(cnt, 1000, ch, cAD.SAMPLE_ASYNC)
                dbgprint(f"StartAsync -> {cAD.pErrorStr}")
                i = 0
                while cAD.pIsBusy:
                    i += 1
                    if (i % 10000) != 0:
                        print(".", end="")
                    time.sleep(0.5) # sec
                print("")
                ret,cnt = cAD.Read()
                dbgprint(f"Read -> {cAD.pErrorStr} / smple -> {cnt}")
                dbgprint("Sampling End")
                
                for i in range(ch):
                    print(f"    {cAD.pCh[i].pName} : {cAD.pCh[i]} {cAD.pCh[i].pUnit}")
                dbgprint(f"A/D Input Time = {"%.3f" % LapStop()} sec")

    # file output(for debug)
    buf = ""
    with open("adinput.csv", "w") as file:
        for j in range(cnt):
            tstr = ""
            for i in range(ch):
                tstr += f"{cAD.pCh[i].pValue[j]},"
            buf += tstr + "\n"
        file.write(buf)
        
    ret = cAD.Close()
    dbgprint(f"Close -> {ret} : {cAD.pErrorStr}")
    
if __name__ == "__main__":
    main()
    if __debug__:
        input("Press Enter > ")


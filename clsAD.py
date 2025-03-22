# coding : utf-8
import sys
#from functools import reduce

import ctypes
import ctypes.wintypes
import caio
import numpy as np

class clsAD:
    ''' clsAD A/D入力クラス
            Note:
                Contec API-AIO(WDM) Ver.8.50対応
    ''' 
    
    # CONSTs
    # 入力モード:pInputMethod
    INPUT_SINGLEEND:int = 0         # シングルエンド入力
    INPUT_DIFFERRENTIAL:int = 1     # 差動入力
    # 転送方式:pTransfer
    TRANSFER_DEVICEBUFFER:int = 0   # デバイスバッファーモード
    TRANSFER_USERBUFFER:int = 1     # ユーザーバッファーモード
    # メモリ形式:pMemoryType
    MEMORY_FIFO:int = 0             # FIFO
    MEMORY_RING:int = 1             # RING
    # クロック種別
    CLOCK_INTERNAL = 0              # 内部クロック
    CLOCK_EXTERNAL = 1              # 外部クロック
    # サンプリング動作
    SAMPLE_SYNC:bool = True         # 同期入力
    SAMPLE_ASYNC:bool = False       # 非同期入力

    def __init__(self):
        ''' clsAD コンストラクタ
                Args: 
                Returns: 
                Note: 
                    Property初期化
        ''' 
        # public property
        self.pOpened:bool = False                   # オープン済フラグ
        self.pName:str = ""                         # ボード名称
        self.pErrorStr:str = ""                     # エラー文字列
        self.pInputMethod:int = self.INPUT_DIFFERRENTIAL   # 入力モード(差動)
        self.pTransfer:int = self.TRANSFER_DEVICEBUFFER  # 転送方式(デバイスバッファ)
        self.pMemoryType:int = self.MEMORY_FIFO          # メモリ形式(FIFO)
        self.pCh:list = []                          # チャンネルクラスリスト
        self.pMaxChannel:int = 0                    # 最大チャンネル数
        self._pID = ctypes.c_short()                # デバイスアクセス用ID
        self._initialized:bool = False              # CH初期化済フラグ
        self._status = ctypes.c_long()              # ADステータス
        # サンプリング設定値
        self._smplsetting:dict = {
                "ChannelCount":0, "SamplingRate":0.0, 
                "SamplingCount":0, "ActualSamplingCount":0, "SampleEventCount":0
            }
        self._ADdata:list = []                      # 入力データ(Digital)

    class clsChannel():
        ''' clsChannel A/Dチャンネルクラス
                Note: 
        ''' 
        def __init__(self, index:int):
            ''' clsChannel コンストラクタ
                    Args: 
                        index(int): チャンネル番号(0~)
                    Returns: 
                    Note: 
                        Property初期化
            ''' 
            # public property
            self.pName:str = f"ch{index}"
            self.pData:np.array = None          # digital data
            self.pValue:np.array = None         # value data
            self.pAverage:list = [0.0, 0.0,]    # value, digital,
            self.pRange:int = 0                 # input range
            self.pMax:float = 10.0              # max value
            self.pMin:float = -10.0             # min value
            self.pOffset:float = 0.0            # value offset
            self.pFormat:str = "{0:.3f}"        # format string (use str.format)
            self.pUnit:str = "V"                # unit of value
            self.pResolution:int = 12           # bitwise(10|12|16|0)
            # private property
            self._count:int = 0                 # sampling count
            self._index:int = index             # channel number
            self._deviceName = ""               # deviceName/exm. "AIO000"
    
        def __str__(self):
            ''' 文字列化メソッド
                    Args: 
                    Returns: 
                        .pAverage[0]の内容を返す
                    Note: 
            ''' 
            return self.pFormat.format(self.pAverage[0])# + self.pUnit
    
        def SetData(self, data:list, cnt:int):
            ''' 各データ設定メソッド
                    Args: 
                        data(list): Digital値のlist
                        cnt(int): dataの個数
                    Returns: 
                    Note: 
                        .pDataを受け、
                        .pValueを計算する
                        ※.pVoltはオミット
            ''' 
            self._count = cnt
            self.pData = np.array(data)
            self.pAverage[1] = self.pData.sum() / self.pData.size   # digital ave.
            self.pAverage[0] = self._toValue(self.pAverage[1])      # value ave
            self.pValue = self._toValue(self.pData)                 # value

        def toVolt(self, d:int) -> float:
            ''' 電圧変換メソッド
                    Args: 
                        d(int): digital値
                    Returns: 
                        変換後の電圧値
                    Note: 
                        _convRangeの返り値と.pResolutionを使用し電圧へ変換する
                        (ボードによっては電流もある)
                        ※pVoltをオミットしたのでパブリック化
            ''' 
            ret:float = 0
            reso:float = 2 ** self.pResolution
            min, max = self._convRange(self.pRange)
            ret = ((max - min) / reso) * d + min
            return ret
            
        def _toValue(self, d:int) -> float:
            ''' 数値変換メソッド
                    Args: 
                        d(int): digital値
                    Returns: 
                        変換後の数値
                    Note: 
                        .pMin/.pMax/.pOffset/.pResolutionを使用し数値へ変換する
            ''' 
            ret:float = 0
            #reso:float = 2 ** self.pResolution
            #max:float = self.pMax
            #min:float = self.pMin
            #off:float = self.pOffset
            #ret = ((max - min) / reso ) * d + min + off
            ret = ((self.pMax - self.pMin) / (2 ** self.pResolution) ) * d + self.pMin + self.pOffset
            ### print(f"{max=} : {min=} : {reso=} : {d=}")
            return ret
        
        def _convRange(self, rng:int) -> (float,float):
            ''' レンジ変換メソッド
                    Args: 
                        rng(int): レンジ指定値
                            (0-14|50-62|100-102|150)
                    Returns: 
                        指定レンジの(最小値,最大値)を返す
                    Note: 
                        一応、全レンジ対応(してるはず)
            ''' 
            mx:float = 10.0
            mn:float = -10.0
            match rng:
                case caio.PM10:       # +/-10V          :=0
                    mx:float = 10.0
                    mn:float = mx * -1
                case caio.PM5:        # +/-5V
                    mx:float = 5.0
                    mn:float = mx * -1
                case caio.PM25:       # +/-2.5V
                    mx:float = 2.5
                    mn:float = mx * -1
                case caio.PM125:      # +/-1.25V
                    mx:float = 1.25
                    mn:float = mx * -1
                case caio.PM1:        # +/-1V
                    mx:float = 1.0
                    mn:float = mx * -1
                case caio.PM0625:     # +/-0.625V
                    mx:float = 0.625
                    mn:float = mx * -1
                case caio.PM05:       # +/-0.5V
                    mx:float = 0.5
                    mn:float = mx * -1
                case caio.PM03125:    # +/-0.3125V
                    mx:float = 0.3125
                    mn:float = mx * -1
                case caio.PM025:      # +/-0.25V
                    mx:float = 0.25
                    mn:float = mx * -1
                case caio.PM0125:     # +/-0.125V
                    mx:float = 0.125
                    mn:float = mx * -1
                case caio.PM01:       # +/-0.1V
                    mx:float = 0.1
                    mn:float = mx * -1
                case caio.PM005:      # +/-0.05V
                    mx:float = 0.05
                    mn:float = mx * -1
                case caio.PM0025:     # +/-0.025V
                    mx:float = 0.025
                    mn:float = mx * -1
                case caio.PM00125:    # +/-0.0125V
                    mx:float = 0.0125
                    mn:float = mx * -1
                case caio.PM001:      # +/-0.01V
                    mx:float = 0.01
                    mn:float = mx * -1
                case caio.P10:        # 0 ~ 10V     :=50
                    mx:float = 10.0
                    mn:float = 0.0
                case caio.P5:         # 0 ~ 5V
                    mx:float = 5.0
                    mn:float = 0.0
                case caio.P4095:      # 0 ~ 4.095V
                    mx:float = 4.095
                    mn:float = 0.0
                case caio.P25:        # 0 ~ 2.5V
                    mx:float = 2.5
                    mn:float = 0.0
                case caio.P125:       # 0 ~ 1.25V
                    mx:float = 1.25
                    mn:float = 0.0
                case caio.P1:         # 0 ~ 1V
                    mx:float = 1.0
                    mn:float = 0.0
                case caio.P05:        # 0 ~ 0.5V
                    mx:float = 0.5
                    mn:float = 0.0
                case caio.P025:       # 0 ~ 0.25V
                    mx:float = 0.25
                    mn:float = 0.0
                case caio.P01:        # 0 ~ 0.1V
                    mx:float = 0.1
                    mn:float = 0.0
                case caio.P005:       # 0 ~ 0.05V
                    mx:float = 0.05
                    mn:float = 0.0
                case caio.P0025:      # 0 ~ 0.025V
                    mx:float = 0.025
                    mn:float = 0.0
                case caio.P00125:     # 0 ~ 0.0125V
                    mx:float = 0.0125
                    mn:float = 0.0
                case caio.P001:       # 0 ~ 0.01V
                    mx:float = 0.01
                    mn:float = 0.0
                case caio.P20MA:      # 0 ~ 20mA        :=100
                    mx:float = 20.0
                    mn:float = 0.0
                case caio.P4TO20MA:   # 4 ~ 20mA
                    mx:float = 20.0
                    mn:float = 4.0
                case caio.PM20MA:     # +/-20mA
                    mx:float = 20.0
                    mn:float = mx * -1
                case caio.P1TO5:      # 1 ~ 5V          :=150
                    mx:float = 5.0
                    mn:float = 1.0
            return mn,mx
        # end clsChannel
        
    def Open(self, deviceName:str) -> int:
        ''' ボードオープンメソッド
                Args: 
                    deviceName(str): ボードのデバイス名(exm.'AIO000')
                Returns: 
                    エラーコード
                    0以外の場合はエラー
                Note:
        ''' 
        lret = ctypes.c_long(0)
        lret.value = caio.AioInit(deviceName.encode(), ctypes.byref(self._pID))
        self._ErrorHandler(lret)
        if lret.value == 0:
            self.pOpened = True
            self._initializeAD(deviceName)
            self._deviceName  = deviceName
        return lret.value
        
    def Close(self) -> int:
        ''' ボードクローズメソッド
                Args: 
                Returns: 
                    エラーコード
                Note: 
        ''' 
        lret = ctypes.c_long(0)
        if self.pOpened:
            lret.value = caio.AioExit(self._pID)
            self._ErrorHandler(lret)
            if lret.value == 0:
                self.pOpened = False
        return lret.value
        
    def Reset(self) -> int:
        ''' リセットメソッド
                Args: 
                Returns: 
                    エラーコード
                    0以外の場合はエラー
                Note: 
        ''' 
        lret = ctypes.c_long(0)
        # プロセスリセット/通常使用は推奨されない
        lret.value = caio.AioResetProcess(self._pID)
        self._ErrorHandler(lret)
        if lret.value:
            return lret.value
        # デバイスリセット
        lret.value = caio.AioResetDevice(self._pID)
        self._ErrorHandler(lret)
        if lret.value:
            return lret.value
        self._initializeAD(self._deviceName)
        lret.value = self.SetRange()
        return lret.value
        
    def Start(self, smpcnt:int, smprate:int, chcnt:int, sync:bool, eventCnt:int=0) -> int:
        ''' A/Dサンプリング開始メソッド
                Args: 
                    smpcnt(int): サンプリング数
                    smprate(int): サンプリングレート(μsec/1000usec==1msec)
                    chcnt(int): 入力チャンネル数
                    sync(bool): 同期フラグ
                                真の場合は、入力完了まで待ち、データを読み込む
                    eventCnt(int): サンプルイベント回数、Defaultは0
                                0以外を指定すると[pIsDataNum]が指定回数で真になる
                                0の場合は常に偽のまま
                Returns:
                    エラーコード
                    0以外の場合はエラー
                Note: 
                    長時間サンプリングの場合は[sync=True/eventCnt>0]を指定し、
                    Start後[pIsDataNum]を監視し、適宜mReadを実行する
                    必要であればStopで停止する
        ''' 
        lret = ctypes.c_long(0)
        
        # 入力チャンネル数設定
        lret.value = caio.AioSetAiChannels(self._pID, chcnt)
        self._ErrorHandler(lret)
        if lret.value:
            return lret.value
        self._smplsetting["ChannelCount"] = chcnt   # チャンネル数

        # サンプリングレート設定
        lret.value = caio.AioSetAiSamplingClock(self._pID, smprate)
        self._ErrorHandler(lret)
        if lret.value:
            return lret.value
        self._smplsetting["SamplingRate"] = smprate # サンプリングレート

        # サンプリング数設定
        lret.value = caio.AioSetAiStopTimes(self._pID, smpcnt)
        self._ErrorHandler(lret)
        if lret.value:
            return lret.value
        self._smplsetting["SamplingCount"] = smpcnt     # サンプリング回数
        lret.value = caio.AioSetAiRepeatTimes(self._pID, 1)     # リピート回数 * 1
        
        # 指定サンプルイベント回数
        lret.value = caio.AioSetAiEventSamplingTimes (self._pID, eventCnt)
        self._ErrorHandler(lret)
        if lret.value:
            return lret.value
        self._smplsetting["SampleEventCount"] = eventCnt     # サンプルイベント回数

        # 開始条件設定(ソフトウェア)
        lret.value = caio.AioSetAiStartTrigger(self._pID, 0)
        self._ErrorHandler(lret)
        if lret.value:
            return lret.value

        # 停止条件設定(設定回数)
        lret.value = caio.AioSetAiStopTrigger(self._pID, 0)
        self._ErrorHandler(lret)
        if lret.value:
            return lret.value

        # メモリリセット
        lret.value = caio.AioResetAiMemory(self._pID)
        self._ErrorHandler(lret)
        if lret.value:
            return lret.value

        # 変換開始
        lret.value = caio.AioStartAi(self._pID)
        self._ErrorHandler(lret)
        if lret.value:
            return lret.value
            
        if sync:    # 同期入力
            while self.pIsBusy():
                if not self.pIsBusy():
                    break

            self.Read()

        return lret.value
    
    def Stop(self) -> int:
        ''' A/Dサンプリング停止メソッド
                Args: 
                Returns: 
                    エラーコード
                    0以外の場合はエラー
                Note: 
        ''' 
        lret = ctypes.c_long(0)
        lret.value = caio.AioStopAi(self._pID)
        self._ErrorHandler(lret)
        return lret.value
        
    def Read(self) -> (int,int):
        ''' A/Dデータ取得
                Args: 
                Returns: 
                    エラーコードとサンプリング数を返す
                Note: 
                    self._ADdata[ch][cnt]に生のデジタル値を取得
        ''' 
        lret = ctypes.c_long()
        smplcnt = ctypes.c_long()
        # サンプリング回数の取得
        lret.value = caio.AioGetAiSamplingCount (self._pID, ctypes.byref(smplcnt))
        self._ErrorHandler(lret)
        if lret.value:
            return lret.value
        self._smplsetting["ActualSamplingCount"] = smplcnt.value    # 実サンプリング回数
        # データ取得
        cnt = self._smplsetting["ActualSamplingCount"]
        ch = self._smplsetting["ChannelCount"]
        AiDataType = ctypes.c_long * (cnt * ch)
        AiData = AiDataType()
        lret.value = caio.AioGetAiSamplingData (self._pID, ctypes.byref(smplcnt), AiData)
        self._ErrorHandler(lret)
        if lret.value:
            return lret.value
        # self._ADdata:list = [[0]*cnt] * ch この宣言の仕方では想定どうりに動かない
        self._ADdata = [[0] * cnt for i in range(ch)]  # _ADdata[ch][cnt]
        for i in range(ch):
            for j in range(cnt):
                self._ADdata[i][j] = AiData[(j * ch) + i]
        #for i in range(ch):     # clsChannelにデータをセット
            self.pCh[i].SetData(self._ADdata[i], cnt)
            
        return lret.value, cnt  # ErrorCode, SamplingCount
        
    def SetRange(self) -> int:
        ''' レンジ設定メソッド
                Args: 
                Returns: 
                    エラーコード
                    0以外の場合はエラー
                Note: 
                    cslChannel.pRangeをボードに設定
                    _initializedを真に設定
        ''' 
        lret = ctypes.c_long(0)
        for i in range(self.pMaxChannel):
            lret.value = caio.AioSetAiRange(self._pID, i, self.pCh[i].pRange)
            self._ErrorHandler(lret)
            if lret.value:
                return lret.value
        self._initialized = True
        return lret.value

    def pIsBusy(self) -> bool:
        ''' デバイス動作中
                Args: 
                Returns: bool
                Note: 
                    変換動作中であれば真
        ''' 
        return self._GetStatus(caio.AIS_BUSY)
        
    def pIsSttTrgr(self) -> bool:
        ''' 開始トリガ待ち
                Args: 
                Returns: bool
                Note: 
                    変換開始トリガ待ちであれば真
        ''' 
        return self._GetStatus(caio.AIS_START_TRG)
        
    def pIsDataNum(self) -> bool:
        ''' 指定サンプリング回数格納
                Args: 
                Returns: bool
                Note: 
                    指定回数のサンプリングが済んでいれば真
        ''' 
        return self._GetStatus(caio.AIS_DATA_NUM)
        
    def pIsOfErr(self) -> bool:
        ''' オーバーフロー
                Args: 
                Returns: bool
                Note: 
                    高機能アナログ入力を実行中、メモリのすべてに変換データが格納され、
                    これ以上データが格納できない状態で
                    さらに変換データを格納しようとすると発生します。

                    ・メモリ形式がFIFOの場合、変換が停止します
                    ・メモリ形式がRINGの場合、変換は継続し過去のデータは上書きされます
        ''' 
        return self._GetStatus(caio.AIS_OFERR)
     
    def pIsScErr(self) -> bool:
        ''' サンプリングクロック周期エラー
                Args: 
                Returns: bool
                Note: 
                    サンプリングクロック周期が速すぎるために起きるエラーです。
                    このエラーが発生すると変換は停止します。
        ''' 
        return self._GetStatus(caio.AIS_SCERR)
        
    def pIsAiErr(self) -> bool:
        ''' A/D変換エラー
                Args: 
                Returns: bool
                Note: 
                    デバイスの変換中ステータスがOFFにならない状態（変換終了しない状態）が
                    長く続いた場合、デバイスドライバは動作異常と判断してこのステータスをONにします。

                    通常このステータスがONになることはありませんが、万一発生する場合は、
                    テクニカルサポートセンターへお問い合わせください。
                    デバイスが故障している可能性があります。
        ''' 
        return self._GetStatus(caio.AIS_AIERR)
        
    def pIsDrvErr(self) -> bool:
        ''' ドライバスペックエラー
                Args: 
                Returns: bool
                Note: 
                    ドライバでの処理が間に合わない場合に発生するエラーです。

                    このエラーはサンプリングクロック周期エラー【20000H】と同時に発生し、
                    結果、【A0000H】となります。
                    なお、デバイスドライバの処理時間は環境により異なります。

                    ソフトウェアメモリを使用するデバイスの場合、
                    変換には [デバイスの変換速度＋デバイスドライバの処理時間] が必要になります。
        ''' 
        return self._GetStatus(caio.AIS_DRVERR)
    
    def _initializeAD(self, devnm:str):
        ''' ボード初期化メソッド
                Args: 
                    devnm(str): ボードのデバイス名(exm.'AIO000')
                Returns: 
                    エラーコード
                    0以外の場合はエラー
                Note: 
                    各ボード毎の初期化処理
                    デフォルトの設定は以下の通り
                        内部クロック(固定)/差動入力/デバイスバッファ/
                        FIFOメモリ/レンジ:±10V
        ''' 
        lret = ctypes.c_long(0)
        deviceName = ctypes.create_string_buffer(256)   # exm."AIO000"
        device = ctypes.create_string_buffer(256)       # exm."AD12-64(PCI)"
        
        if __debug__:      # プロセスリセット/通常使用は推奨されない
            lret.value = caio.AioResetProcess(self._pID)
        # デバイスリセット
        lret.value = caio.AioResetDevice(self._pID)
        # デバイス名称の取得
        if not self._initialized:       # 初回のみ
            i = 0
            while i < 255:
                # ボードが複数の場合に対応
                lret.value = caio.AioQueryDeviceName (i,deviceName ,device )
                i += 1
                if lret.value:
                    self._ErrorHandler(lret)
                elif deviceName.value.decode('sjis') == devnm:
                    self.pName = device.value.decode('sjis')
                    break
        
        # 入力方式(差動)
        lret.value = caio.AioSetAiInputMethod(self._pID, self.pInputMethod)
        self._ErrorHandler(lret)
        # 転送方式（デバイスバッファモード）
        lret.value = caio.AioSetAiTransferMode(self._pID, self.pTransfer)
        self._ErrorHandler(lret)
        # メモリー形式設定(FIFO)
        lret.value = caio.AioSetAiMemoryType(self._pID, self.pMemoryType)
        self._ErrorHandler(lret)
        # 分解能の取得(bit数:10|12|16|0)
        self._reso = ctypes.c_short()
        lret.value = caio.AioGetAiResolution(self._pID, ctypes.byref(self._reso))
        self._ErrorHandler(lret)
        if lret.value:
            return lret.value
        # 最大チャンネル数の取得
        maxch = ctypes.c_short()
        lret.value = caio.AioGetAiMaxChannels(self._pID, ctypes.byref(maxch))
        self._ErrorHandler(lret)
        self.pMaxChannel = maxch.value
        if not self._initialized:       # 初回のみ
            # clsChannelのインスタンス化
            self.pCh = [self.clsChannel] * self.pMaxChannel
            for i in range(self.pMaxChannel): 
                self.pCh[i] = self.clsChannel(i)
                self.pCh[i].pResolution = self._reso.value

        # クロック種別(内部クロック固定)
        lret.value = caio.AioSetAiClockType(self._pID, self.CLOCK_INTERNAL)
        self._ErrorHandler(lret)
        if lret.value:
            return lret.value

        return lret.value

    def _GetStatus(self, stat:int) -> bool:
        ''' A/Dステータス取得メソッド
                Args: 
                    stat(int): caio.AIS_*
                        AIS_BUSY = 0x00000001           # Device is working
                        AIS_START_TRG = 0x00000002      # Wait the start trigger
                        AIS_DATA_NUM = 0x00000010       # Store the data of the specified number of samplings
                        AIS_OFERR = 0x00010000          # Overflow
                        AIS_SCERR = 0x00020000          # Sampling clock error
                        AIS_AIERR = 0x00040000          # AD converting error
                        AIS_DRVERR = 0x00080000         # Driver spec error
                Returns: 
                    self._status & stat が0以外であれば真
                Note: 
        ''' 
        lret = ctypes.c_long(0)
        
        lret.value = caio.AioGetAiStatus (self._pID, ctypes.byref(self._status))
        self._ErrorHandler(lret)
        return (self._status.value & stat) != 0
        
    def _ErrorHandler(self, ecode:ctypes.c_long) -> str:
        ''' エラー文字列取得メソッド
                Args: 
                    ecode(ctypes.c_long): エラーコード
                Returns: 
                    エラー文字列
                Note: 
                    エラー文字列をself.pErrorStrに設定
        ''' 
        error_buf = ctypes.create_string_buffer(256)
        caio.AioGetErrorString(ecode, error_buf)
        self.pErrorStr = f"[{ecode.value}] {error_buf.value.decode('sjis')}"
        if ecode.value != 0:
            print(self.pErrorStr, file=sys.stderr)
        return self.pErrorStr


import tkinter
from tkcalendar import DateEntry
import datetime
import os
import wget
import subprocess
import glob
from unlzw import unlzw
from tecvalues import driver
from IonexWriter import writeionex
import threading
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from scipy.interpolate import griddata
import csv
import time
import matplotlib.animation as animation
from ftplib import FTP

selected = []
dayyofyear = ''
stringdate = ''

#Providing interface to select the GPS stations
def selectstns():
    def run():
        def on_click():
            for station, intvar in zip(stations, intvars):
                if intvar.get() == 1 and not station in selected:
                    selected.append(station)
                elif intvar.get() == 0 and station in selected:
                    selected.remove(station)
            master.destroy()

        master = tkinter.Tk()
        master.title("Select Stations")
        mydict = {}
        reader = csv.reader(open('stations.csv','r'))
        header = next(reader)
        for row in reader:
            mydict[row[0].lower()] = {header[1]:row[1],header[2]:row[2],header[3]:row[3],header[4]:row[4],header[5]:row[5]}
        stations = mydict.keys()
        intvars = []
        checkbuttons = []
        for station in stations:
            intvar = tkinter.IntVar(master)
            if station in selected:
                intvar.set(1)
            checkbutton = tkinter.Checkbutton(master, text=mydict[station][header[1]], variable=intvar)
            checkbutton.pack(anchor='w')
            intvars.append(intvar)
            checkbuttons.append(checkbutton)

        button = tkinter.Button(master, text="Done", command=on_click)
        button.pack()

        master.mainloop()
    thread1 = threading.Thread(target=run)
    thread1.start()

#For plotting and visualizing the data
def plotter():
    dirpath='data\\'+stringdate[0:4]+'\\'+dayyofyear
    filepath = dirpath+'\\TECValues.csv'
    mydateparser = lambda x: pd.datetime.strptime(x, "%d-%b-%Y (%H:%M:%S)")
    dataframe = pd.read_csv(filepath, parse_dates=['Datetime'],date_parser=mydateparser)
    writeionex(dataframe,dirpath)
    timelist = dataframe['Datetime'].tolist()
    timelist = set(timelist)
    timelist = sorted(timelist)
    f = plt.figure()
    def animate(i):
        f.clear()
        ax = plt.subplot(1,1,1)
        subdataframe = dataframe.loc[dataframe['Datetime'] == timelist[i]]
        y = subdataframe['lat'].to_numpy()
        x = subdataframe['lon'].to_numpy()
        z = subdataframe['verticaltec'].to_numpy()
        xi = np.linspace(80,89,20)
        yi = np.linspace(26,31,12)
        zi = griddata((x, y), z, (xi[None,:], yi[:,None]), method='linear',rescale=True)
        cf = ax.contourf(xi,yi,zi,levels=20,cmap='gist_rainbow',alpha=0.3,antialiased=True)
        ax.set(xlim=(80, 89), ylim=(26, 31))
        ax.set_title('TEC map of '+timelist[i].strftime("%d-%b-%Y (%H:%M:%S)")+" UTC")
        ax.set_xlabel('Longitude [Degrees]')
        ax.set_ylabel('Latitude [Degrees]')
        plt.imshow(plt.imread(r'map.JPG'), alpha=1, extent=[80,89,26,31])
        cbar = plt.colorbar(cf)
        cbar.ax.set_ylabel('TECU [10^16 electrons/sq. m]', rotation=270,labelpad=10)
        #plt.savefig(timelist[i].strftime("%d-%b-%Y (%H-%M-%S)")+'.png',bbox_inches='tight')
        return ax

    ani = animation.FuncAnimation(f,animate,len(timelist),interval=1*1e+3,blit=False)
    #f.colorbar(cf, ax=ax)
    plt.show()

#Download DCB files from CODE
def getdcbfiles(stringdate,dirpath):
    ftp = FTP('ftp.aiub.unibe.ch')
    ftp.login('anonymous','anonymous')
    ftp.cwd('/CODE/'+stringdate[0:4])
    downfilestr1='RETR P1C1'+stringdate[2:4]+stringdate[5:7]+'.DCB.Z'
    downfilestr2='RETR P1P2'+stringdate[2:4]+stringdate[5:7]+'.DCB.Z'
    filestr1 = dirpath+'\\P1C1'+stringdate[2:4]+stringdate[5:7]+'.DCB.Z'
    filestr2 = dirpath+'\\P1P2'+stringdate[2:4]+stringdate[5:7]+'.DCB.Z'
    if datetime.datetime.now().strftime('%m') == stringdate[5:7] and datetime.datetime.now().strftime('%Y') == stringdate[0:4]:
        ftp.cwd('..')
        downfilestr1='RETR P1C1.DCB'
        downfilestr2='RETR P1P2.DCB'
        filestr1 = dirpath+'\\P1C1'+stringdate[2:4]+stringdate[5:7]+'.DCB'
        filestr2 = dirpath+'\\P1P2'+stringdate[2:4]+stringdate[5:7]+'.DCB'
    if not os.path.exists(filestr1):
        p1c1File = open(filestr1, 'wb')
        ftp.retrbinary(downfilestr1, p1c1File.write)
        p1c1File.close()
    if not os.path.exists(filestr2):
        p1p2File = open(filestr2, 'wb')
        ftp.retrbinary(downfilestr2, p1p2File.write)
        p1p2File.close()
    ftp.close()

#Download the GNSS Data from UNAVCO site and DCB from CODE
def downloaddata():
    global dayyofyear,stringdate
    dayyofyear = cal.get_date().strftime('%j')
    stringdate = str(cal.get_date()) #2019-09-02
    i = 0
    dirpath = 'data\\'+stringdate[0:4]+'\\'+dayyofyear
    for each in selected:
        statuslabel.config (text="Dowloading data of:"+each)
        progressbar['value']=((i/len(selected))*100)
        root.update()
        i = i+1
        urlstringobs = 'ftp://data-out.unavco.org/pub/rinex/obs/'+stringdate[0:4]+'/'+dayyofyear+'/'+each+dayyofyear+'0.'+stringdate[2:4]+'d.Z'
        urlstringnav = 'ftp://data-out.unavco.org/pub/rinex/nav/'+stringdate[0:4]+'/'+dayyofyear+'/'+each+dayyofyear+'0.'+stringdate[2:4]+'n.Z'
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)
        try:
            if not os.path.exists(dirpath+'\\'+each+dayyofyear+'0.'+stringdate[2:4]+'d.Z'):
                wget.download(urlstringobs,out=dirpath)
            if not os.path.exists(dirpath+'\\'+each+dayyofyear+'0.'+stringdate[2:4]+'n.Z'):
                wget.download(urlstringnav,out=dirpath)
        except:
            continue
    statuslabel.config (text="Downloading DCB files")
    getdcbfiles(stringdate,dirpath)
    progressbar['value']=100
    statuslabel.config (text="Download Complete")

#Processing the GPS data and getting the CSV file out of it
def process():
    def subfunction():
        starttime = stringdate+"T"+str(starthourvar.get())+':'+str(startminvar.get())
        stoptime = stringdate+"T"+str(stophourvar.get())+':'+str(stopminvar.get())+':45'
        timegap = gaptimevar.get()
        dirpath = 'data\\'+stringdate[0:4]+'\\'+dayyofyear
        navfiles = glob.glob(dirpath+'\\*.'+stringdate[2:4]+'n.Z')
        obsfiles = glob.glob(dirpath+'\\*.'+stringdate[2:4]+'d.Z')
        dcbfiles = glob.glob(dirpath+'\\*.DCB.Z')
        progressbar['value']=0
        statuslabel.config (text='Decompressing Files')
        root.update()
        decompressnav(navfiles)
        decompressobs(obsfiles)
        decompressdcb(dcbfiles)
        statuslabel.config (text='Decompressing Done')
        root.update()
        satdcbsintecu = {}
        p1c1dcbfile = open(dirpath+'\\P1C1'+stringdate[2:4]+stringdate[5:7]+'.DCB','r').readlines()[7:39]
        p1p2dcbfile = open(dirpath+'\\P1P2'+stringdate[2:4]+stringdate[5:7]+'.DCB','r').readlines()[7:39]
        for line1,line2 in zip(p1c1dcbfile,p1p2dcbfile):
            satdcbsintecu[line1.split()[0]]=(float(line1.split()[1])+float(line2.split()[1]))*2.85
        dotofiles = glob.glob(dirpath+'\\'+'*.'+stringdate[2:4]+'o')
        dotnfiles = glob.glob(dirpath+'\\'+'*.'+stringdate[2:4]+'n')
        csvfile = open(dirpath+'\\TECValues.csv','w')
        csvfile.write('Datetime,Satnum,slanttec,elevationangle,verticaltec,lat,lon\n')
        i = 0
        for (obs,nav) in zip(dotofiles,dotnfiles):
            progressbar['value']=((i/len(dotnfiles))*100)
            i=i+1
            statuslabel.config(text="Processing file:"+obs)
            root.update()
            csvdata = driver(obs,nav,starttime,stoptime,timegap,satdcbsintecu)
            csvfile.write(csvdata)
        csvfile.close()
        statuslabel.config(text="Processing Done")
        progressbar['value']=100
        root.update()
    thread2 = threading.Thread(target=subfunction)
    thread2.start()

#Converting .xxn.z files to .xxn files
def decompressnav(navfiles):
    for each in navfiles:
        infile = open(each,'rb+')
        incontent = infile.read()
        outcontent = unlzw(incontent)
        outfile = open(each[0:-2],'wb')
        outfile.write(outcontent)
        outfile.close()

#Converting .DCB.z files to .DCB files
def decompressdcb(dcbfiles):
    for each in dcbfiles:
        infile = open(each,'rb+')
        incontent = infile.read()
        outcontent = unlzw(incontent)
        outfile = open(each[0:-2],'wb')
        outfile.write(outcontent)
        outfile.close()

#Converting .xxd.z files to .xxo files
def decompressobs(obsfiles):
    for each in obsfiles:
        infile = open(each,'rb+')
        incontent = infile.read()
        outcontent = unlzw(incontent)
        outfile = open(each[0:-2],'wb')
        outfile.write(outcontent)
        outfile.close()
        subprocess.call('tools\\crx2rnx -f '+each[0:-2],shell=True)

#GUI part of the program
root = tkinter.Tk()
root.title('Ionospheric map preparation software')
upperframe = tkinter.Frame(root)
upperframe.pack()
cal = DateEntry(upperframe,firstweekday='sunday',showweeknumbers=False, width=12, background='darkblue', foreground='white', borderwidth=2, mindate= datetime.date(2018,1,1), maxdate= datetime.date.today())
cal.pack(padx=5, pady=10,side=tkinter.LEFT)
selectstationbutton = tkinter.Button(upperframe, text="Select Stations", command=selectstns)
selectstationbutton.pack(padx=5, pady=10,side=tkinter.LEFT)
getdata = tkinter.Button(upperframe, text="Get Data", command=downloaddata)
getdata.pack(padx=5, pady=10,side=tkinter.LEFT)
tkinter.Label(upperframe,text="Start Time (HH:MM)").pack(padx=5,pady=10,side=tkinter.LEFT)
hourlist = tuple(range(0,24))
starthourvar = tkinter.IntVar(root)
starthourvar.set(hourlist[0])
startHour = tkinter.OptionMenu(upperframe,starthourvar,*hourlist)
startHour.pack(padx=1, pady=10,side=tkinter.LEFT)
tkinter.Label(upperframe,text=":").pack(side=tkinter.LEFT)
minlist = tuple(range(0,60))
startminvar = tkinter.IntVar(root)
startminvar.set(minlist[0])
startMin = tkinter.OptionMenu(upperframe,startminvar,*minlist)
startMin.pack(padx=1, pady=10,side=tkinter.LEFT)
tkinter.Label(upperframe,text="Stop Time (HH:MM)").pack(padx=5,pady=10,side=tkinter.LEFT)
stophourvar = tkinter.IntVar(root)
stophourvar.set(hourlist[-1])
stopHour = tkinter.OptionMenu(upperframe,stophourvar,*hourlist)
stopHour.pack(padx=1, pady=10,side=tkinter.LEFT)
tkinter.Label(upperframe,text=":").pack(side=tkinter.LEFT)
stopminvar = tkinter.DoubleVar(root)
stopminvar.set(minlist[-1])
stopMin = tkinter.OptionMenu(upperframe,stopminvar,*minlist)
stopMin.pack(padx=1, pady=10,side=tkinter.LEFT)
tkinter.Label(upperframe,text="Time Interval").pack(padx=5,pady=10,side=tkinter.LEFT)
gaptimetist = ('0.25','0.5','1','2','5','10','20','30','60','120')
gaptimevar = tkinter.StringVar(root)
gaptimevar.set(gaptimetist[0])
gapTime = tkinter.OptionMenu(upperframe,gaptimevar,*gaptimetist)
gapTime.pack(padx=1, pady=10,side=tkinter.LEFT)
tkinter.Label(upperframe,text="Minutes").pack(padx=5,pady=10,side=tkinter.LEFT)
processdata = tkinter.Button(upperframe, text="Process Data", command=process)
processdata.pack(padx=5, pady=10,side=tkinter.LEFT)
plotdata = tkinter.Button(upperframe, text="Generate TEC Maps", command=plotter)
plotdata.pack(padx=5, pady=10,side=tkinter.LEFT)
lowerframe = tkinter.Frame(root)
lowerframe.pack(fill='x')
progressbar = tkinter.ttk.Progressbar(lowerframe,orient='horizontal',length=100,mode='determinate')
progressbar.pack(padx=5, pady=5, fill='x')
statuslabel = tkinter.Label(lowerframe,text="Ready")
statuslabel.pack(padx=5, pady=5, fill='x')
root.mainloop()
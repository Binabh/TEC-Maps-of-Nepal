import numpy as np
from scipy.interpolate import griddata
from datetime import datetime

def writeionex(dataframe,dirpath):
    timelist = dataframe['Datetime'].tolist()
    timelist = set(timelist)
    timelist = sorted(timelist)
    #Opening the IONEX file
    ionexfile = open(dirpath+'\\nepal'+timelist[0].strftime('%j')+'0.'+timelist[0].strftime('%y')+'i','w+')
    header = """     1.0            IONOSPHERE MAPS     GNSS                IONEX VERSION / TYPE
FinalProjV1         KU                  {today}     PGM / RUN BY / DATE 
Ionospheric Model generated using CORS data of Nepal        COMMENT             
Regional Ionospheric Model of Nepal. This is the product    DESCRIPTION
of final year project of Undergraduate at Kathmandu         DESCRIPTION
University                                                  DESCRIPTION
Contact address: binabhdevkota@gmail.com                    DESCRIPTION                  
  {start}                   EPOCH OF FIRST MAP  
  {end}                   EPOCH OF LAST MAP   
  {interval}                                                      INTERVAL            
    {nofmaps}                                                      # OF MAPS IN FILE
    COSZ                                                    MAPPING FUNCTION
     0.0                                                    ELEVATION CUTOFF          
Pseudorange values with DCB correction                      OBSERVABLES USED            
  6371.0                                                    BASE RADIUS         
     2                                                      MAP DIMENSION       
   400.0 400.0   0.0                                        HGT1 / HGT2 / DHGT  
    80.0 89.0  0.5                                          LAT1 / LAT2 / DLAT  
    26.0 31.0  0.5                                          LON1 / LON2 / DLON  
    -1                                                      EXPONENT            
TEC/RMS values in 0.1 TECU; 9999, if no value available     COMMENT             
                                                            END OF HEADER\n""".format(today = datetime.now().strftime("%d-%b-%y %H:%M"),start=timelist[0].strftime("%Y     %m     %d     %H     %M     %S"),end=timelist[-1].strftime("%Y     %m     %d     %H     %M     %S"),interval=(timelist[1]-timelist[0]).total_seconds(),nofmaps=len(timelist))
    #Writing the header section
    ionexfile.write(header)
    for each in timelist:
        subdataframe = dataframe.loc[dataframe['Datetime'] == each]
        y = subdataframe['lat'].to_numpy()
        x = subdataframe['lon'].to_numpy()
        z = subdataframe['verticaltec'].to_numpy()
        xi = np.linspace(80,89,20)
        yi = np.linspace(26,31,12)
        zi = griddata((x, y), z, (xi[None,:], yi[:,None]), method='linear',rescale=True)
        np.nan_to_num(zi,copy=False)
        zi[zi == 0] = 9999
        mapstart = """     {mapnum}                                                      START OF TEC MAP    
  {epoch}                   EPOCH OF CURRENT MAP\n""".format(epoch=each.strftime("%Y     %m     %d     %H     %M     %S"),mapnum=timelist.index(each)+1)
        #Writing the starting of map
        ionexfile.write(mapstart)
        i=0
        for row in zi:
            datasection = """    {lat} 80.0 89.0   0.5 400.0                              LAT/LON1/LON2/DLON/H
    {v1}    {v2}    {v3}    {v4}    {v5}    {v6}    {v7}    {v8}    {v9}    {v10}    {v11}    {v12}    {v13}    {v14}    {v15}    {v16}
    {v17}    {v18}    {v19}    {v20}\n""".format(lat=26+0.5*i,v1=int(row[0]),v2=int(row[1]),v3=int(row[2]),v4=int(row[3]),v5=int(row[4]),v6=int(row[5]),v7=int(row[6]),v8=int(row[7]),v9=int(row[8]),v10=int(row[9]),v11=int(row[10]),v12=int(row[11]),v13=int(row[12]),v14=int(row[13]),v15=int(row[14]),v16=int(row[15]),v17=int(row[16]),v18=int(row[17]),v19=int(row[18]),v20=int(row[19]))
            i=i+1
            #Writing TEC value rows
            ionexfile.write(datasection)
        mapend = """     {mapnum}                                                      END OF TEC MAP      \n""".format(mapnum=timelist.index(each)+1)
        #Writing the map end
        ionexfile.write(mapend)
    fileend = """                                                            END OF FILE         """
    ionexfile.write(fileend)
    #Closing the Ionex file
    ionexfile.close()
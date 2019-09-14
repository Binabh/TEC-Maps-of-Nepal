import georinex as gr
import math
import numpy as np
import pymap3d as pm
import glob

#getting satellite elevation and azimuth
def getsatElev(recposgeo,satpos):
	slat,slon,shei= pm.ecef2geodetic(satpos[0], satpos[1], satpos[2], deg=True)
	az,el,r = pm.geodetic2aer(slat, slon, shei, recposgeo[0], recposgeo[1], recposgeo[2], deg=True)
	return (el,az)

#Getting vertical TEC values using a mapping function
def getVTEC(stec,elev):
	rofearth = 6371000
	hofip = 400000
	mapfunc = math.sqrt(1-((rofearth*math.cos(math.radians(elev)))/(rofearth+hofip))**2)
	vtec = stec*mapfunc
	return vtec

#getting lat and lon of IPP
def getIPPLattLon(recvpos,eleaz):
	rofearth = 6371000
	hofip = 400000
	p = (math.pi/2)-math.radians(eleaz[0])-math.asin((rofearth*math.cos(math.radians(eleaz[0])))/(rofearth+hofip))
	ipplat = math.degrees(math.asin(math.sin(math.radians(recvpos[0]))*math.cos(p)+math.cos(math.radians(recvpos[0]))*math.sin(p)*math.cos(math.radians(eleaz[1]))))
	ipplon = recvpos[1]+math.degrees(math.asin(math.sin(p)*math.sin(math.radians(eleaz[1])/math.cos(math.radians(recvpos[0])))))
	ipplatlon = (ipplat,ipplon)
	return ipplatlon


def getSatXYZ(nav,obssv,obstime):
	xyz = tuple()

	#Constants
	GM = 3.986004418e14
	EMAV = 7.2921151467e-5
	svdata = nav.sel(sv=obssv).dropna(dim='time')
	timedifferences = [abs((t-obstime.to_datetime64())/ np.timedelta64(1,'s')) for t in svdata.coords['time'].values]
	epochtime = svdata.coords['time'].values[timedifferences.index(min(timedifferences))]
	finaldata = svdata.sel(time=epochtime)
	timeeph = finaldata['Toe']
	t = getGpsTime(obstime)-timeeph
	
	#Keplerian Elements
	M0 = finaldata['M0']
	sqrtA = finaldata['sqrtA']
	deltaN = finaldata['DeltaN']
	ecc = finaldata['Eccentricity']
	incli = finaldata['Io']
	rateofIncli = finaldata['IDOT']
	argofperigee = finaldata['omega']
	rightacc = finaldata['Omega0']
	rateofRightAcc = finaldata['OmegaDot']

	#coefficients for correction
	cuc = finaldata['Cuc']
	cus = finaldata['Cus']
	crc = finaldata['Crc']
	crs = finaldata['Crs']
	cic = finaldata['Cic']
	cis = finaldata['Cis']

	#computation for anomalies
	meanAmomaly = M0 + t*(deltaN+ math.sqrt(GM/sqrtA**6))
	ecentricAnomaly = solveIter(meanAmomaly,ecc)
	trueAnomaly = math.atan((math.sqrt(1-ecc**2)*math.sin(ecentricAnomaly))/(math.cos(ecentricAnomaly)-ecc))

	#computation for pertubrations
	phik = argofperigee+trueAnomaly
	argofperigee_comp = argofperigee+cuc*math.cos(2*phik)+cus*math.sin(2*phik)
	radialDistance = (1-ecc*math.cos(ecentricAnomaly))*(sqrtA**2)+crc*math.cos(2*phik)+crs*math.sin(2*phik)
	inclination = incli+rateofIncli*t+cic*math.cos(2*phik)+cis*math.sin(2*phik)

	#computation for right accension
	rightacc_comp = rightacc+t*(rateofRightAcc-EMAV)-(EMAV*timeeph)
	cosra = math.cos(rightacc_comp)
	sinra = math.sin(rightacc_comp)
	cosaop = math.cos(argofperigee_comp)
	sinaop = math.sin(argofperigee_comp)
	cosi = math.cos(inclination)
	sini = math.sin(inclination)
	cosVk = math.cos(meanAmomaly)
	sinVk = math.sin(meanAmomaly)
	smallr = np.array([radialDistance*cosVk,radialDistance*sinVk,0])
	capitalR = np.array([[cosra*cosaop-sinra*sinaop*sini,-1*cosra*sinaop-sinra*cosaop*cosi,sinaop*sini],
				[sinra*cosaop+cosra*sinaop*cosi,-1*sinra*sinaop+cosra*cosaop*cosi,-1*cosra*sini],
				[sinaop*sini,cosaop*sini,cosi]])
	coordsmatrix = np.matmul(capitalR,smallr)
	xyz = (coordsmatrix[0],coordsmatrix[1],coordsmatrix[2])
	return xyz

def getGpsTime(dt):
	"""_getGpsTime returns gps time (seconds since midnight Sat/Sun) for a datetime
	"""
	total = 0
	days = (dt.weekday()+ 1) % 7 # this makes Sunday = 0, Monday = 1, etc.
	total += days*3600*24
	total += dt.hour * 3600
	total += dt.minute * 60
	total += dt.second
	return(total)

def solveIter(mu,e):
	"""
	__solvIter returns an iterative solution for Ek
	Mk = Ek - e sin(Ek)
	adapted to accept vectors instead of single values
	"""
	thisStart = mu-1.01*e
	thisEnd = mu + 1.01*e
	bestGuess = 0

	for i in range(5):
		minErr = 10000
		for j in range(5):
			thisGuess = thisStart + j*(thisEnd-thisStart)/10.0
			thisErr = abs(mu - thisGuess + e*np.sin(thisGuess))
			if (thisErr<minErr):
				minErr = thisErr
				bestGuess = thisGuess

		# reset for next loop
		thisRange = thisEnd - thisStart
		thisStart = bestGuess - thisRange/10.0
		thisEnd = bestGuess + thisRange/10.0

	return(bestGuess)

def driver(obsfile,navfile,start,stop,timegap,satdcb):
	obs = gr.load(obsfile, meas=['L1','L2','C1','P2'], tlim=[start,stop])
	nav = gr.load(navfile)
	finalresult = ''
	testing = gr.load(obsfile)
	testingpoints = testing.coords['time'].values
	if not len(testingpoints) == 5760:
		return finalresult
	points = obs.coords['time'].values
	GPSsats = ('G01', 'G02', 'G03', 'G05', 'G06', 'G07', 'G08', 'G09', 'G10', 'G11',
       'G12', 'G13', 'G14', 'G15', 'G16', 'G17', 'G18', 'G19', 'G20', 'G21',
       'G22', 'G23', 'G24', 'G25', 'G26', 'G27', 'G28', 'G29', 'G30', 'G31',
       'G32')
	for eachepoch in points[::int(float(timegap)*4)]:
		oneepochl1 = obs['L1'].sel(time = eachepoch).dropna(dim='sv')
		oneepochl2 = obs['L2'].sel(time = eachepoch).dropna(dim='sv')
		oneepochc1 = obs['C1'].sel(time = eachepoch).dropna(dim='sv')
		oneepochp2 = obs['P2'].sel(time = eachepoch).dropna(dim='sv')
			
		l1satset = set(oneepochl1.coords['sv'].values)
		l2satset = set(oneepochl2.coords['sv'].values)
		c1satset = set(oneepochc1.coords['sv'].values)
		p2satset = set(oneepochp2.coords['sv'].values)
		commonsats = l1satset.intersection(l2satset)
		commonsats = commonsats.intersection(c1satset)
		commonsats = commonsats.intersection(p2satset)
		commonsats = commonsats.intersection(GPSsats)

		for eachsv in commonsats:
			stamp = eachepoch.strftime("%d-%b-%Y (%H:%M:%S)")
			satelliteno = eachsv
			l1value = oneepochl1.values[oneepochl1.coords['sv'].values.tolist().index(eachsv)]
			l2value = oneepochl2.values[oneepochl2.coords['sv'].values.tolist().index(eachsv)]
			c1value = oneepochc1.values[oneepochc1.coords['sv'].values.tolist().index(eachsv)]
			p2value = oneepochp2.values[oneepochp2.coords['sv'].values.tolist().index(eachsv)]
			stec = 9.5172816799473472 *(p2value - c1value) + satdcb[eachsv]
			satCoord = getSatXYZ(nav,eachsv,eachepoch)
			satelevaz = getsatElev(obs.position_geodetic,satCoord)
			vtec = getVTEC(stec,satelevaz[0])
			if vtec < 0:
				continue
			elif vtec >70:
				continue
			ipplatlon = getIPPLattLon(obs.position_geodetic,satelevaz)
			result = (stamp+","+satelliteno+","+str(stec)+","+str(satelevaz[0])+","+str(vtec)+","+str(ipplatlon[0])+","+str(ipplatlon[1])+"\n")
			finalresult = finalresult+result
	return finalresult
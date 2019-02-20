
import epd2in13
import datetime
import time
import Image
import ImageDraw
import ImageFont
import weatherbitio as wbit
import traceback
import os
import config

#for buttons
import RPi.GPIO as GPIO

#some utils functions
import alan_utils

################################################################################################3
##
##  Constants & Globals
##
################################################################################################3

#Tokyo
CITYCODE="1850147"
KEY=config.weatherio["key"]

PADDING = 5
PATH_TO_FONTS = "fonts/"
PATH_TO_IMG = "retinaweather/"

#key is LOWERCASE!
condition2image = {
    "cloudy": "retina-cloud.png",    
    "cloudy-night": "retina-night-cloud.png",    

    "sunny" : "retina-sunny.png",
    "sunny-night" : "retina-night-clear.png",

    "rain" : "retina-rain.png",
    "rain-night" : "retina-rain.png",

    "snow" : "retina-snow.png",
    "snow-night" : "retina-snow.png",

    "thunder" : "retina-thunder.png",
    "thunder-night" : "retina-thunder.png",

    "mist": "retina-mist.png",
    "mist-night": "retina-mist.png",

    "drizzle": "retina-rain.png",
    "drizzle-night": "retina-rain.png",
    
}

# Pin Definitons: it's the GPIO##, not the Pin number on the connector (beware)
BUTTONPINA = 16
BUTTONPINB = 12

#the epd object for the display
epd = None

#available panels and current one
PANELS = ["Weather", "Shutdown", "Others"]
currentPanelIdx = 0

#Fonts
font_xbig = ImageFont.truetype(os.path.join(PATH_TO_FONTS, 'DisposableDroidBB.ttf'), 48)
font_big = ImageFont.truetype(os.path.join(PATH_TO_FONTS, 'DisposableDroidBB.ttf'), 30)
font_medium = ImageFont.truetype(os.path.join(PATH_TO_FONTS, 'DisposableDroidBB.ttf'), 20)
font_mediumsmall = ImageFont.truetype(os.path.join(PATH_TO_FONTS, 'DisposableDroidBB.ttf'), 18)
font_small = ImageFont.truetype(os.path.join(PATH_TO_FONTS, 'DisposableDroidBB.ttf'), 16)
font_xsmall = ImageFont.truetype(os.path.join(PATH_TO_FONTS, 'DisposableDroidBB.ttf'), 9)

################################################################################################3
##
##  Functions
##
################################################################################################3

#Supposedely calculates moon phases ... just plain wrong :(
def moonPhase1(d):
    #http://www.voidware.com/moon_phase.htm
    y = d.year
    m = d.month
    d = d.day

    if m < 3:
        y = y -1
        m = m + 12
    m = m + 1
    c = 365.25 * y
    e = 30.6 * m
    jd  = c + e + d - 694039.09
    jd = jd / 29.53

    jd = jd - float(int (jd))
    b = jd * 8 + 0.5
    b = b % 8
    return b


#Get the forecast every 3h for 24h
def getWeather(forecastIndex):
    w = wbit.getNext24hby3h(KEY, CITYCODE)["data"][forecastIndex]
    print(w)
    return w

#Get CURRENT weather
def getWeatherNow():
    w = wbit.getCurrentWeather(KEY, CITYCODE)
    print(w)
    return w



def getWeatherTomorrow():
    return "Tomorrow is " +getWeather (7)



def getImageFromCondition(condition, when):
    c = condition
    if when.hour < 8 or when.hour >= 20:
        c = c +  "-night"
        
    #print("DEBUG: search image for '%s' at %s." % (c, when))
    if c in condition2image: 
        return condition2image[c]
    else:
        return "unknown.png"

#Draws the moon according it's phase (it's a square)
def drawMoon():
    phase = moonPhase1(now)
    basex = image_width - 50
    basey = 70
    moonw = 40
    moonh = 35
    draw.text((basex + 4, basey + moonh + 1), "Moon", font=font_small, fill = 0)
    #ext rectangle
    draw.rectangle ([ (basex, basey) , (basex + moonw, basey + moonh)], outline = 0)
    #in color
    if phase == 0:
        #new moon - all black
        draw.rectangle ([ (basex +2 , basey+2) , (basex + moonw - 2, basey + moonh-2 )], outline = 0, fill = 0)
    elif phase == 1:
        draw.rectangle ([ (basex +2 , basey+2) , (basex + (moonw * 0.75) - 2, basey + moonh-2 )], outline = 0, fill = 0)
    elif phase == 2:
        draw.rectangle ([ (basex +2 , basey+2) , (basex + (moonw * 0.5) - 2, basey + moonh-2 )], outline = 0, fill = 0)
    elif phase == 3:
        draw.rectangle ([ (basex +2 , basey+2) , (basex + (moonw * 0.25) - 2, basey + moonh-2 )], outline = 0, fill = 0)
    elif phase == 4:
        #fullmoon
        pass
    elif phase == 5:
        draw.rectangle ([ (basex +2 + (moonw * 0.75) , basey+2) , (basex + moonw - 2, basey + moonh-2 )], outline = 0, fill = 0)
    elif phase == 6:
        draw.rectangle ([ (basex +2 + (moonw * 0.5) , basey+2) , (basex + moonw - 2, basey + moonh-2 )], outline = 0, fill = 0)
    elif phase == 7:
        draw.rectangle ([ (basex +2 + (moonw * 0.25) , basey+2) , (basex + moonw - 2, basey + moonh-2 )], outline = 0, fill = 0)


#Does the init for the eInk display
def eInkInit():
    epd = epd2in13.EPD()
    epd.init(epd.lut_full_update)

    epd.clear_frame_memory(0xFF)
    #    epd.set_frame_memory(image, 0, 0)
    #    epd.display_frame()
    #    epd.init(epd.lut_partial_update)
    return epd
    

#shows the image parameter on the eInk display
def eInkShow(epd, img):
    epd.set_frame_memory(img, 0, 0)
    epd.display_frame()


#Init the GPIO buttons
def initButtons():
    GPIO.setmode(GPIO.BCM) # Broadcom pin-numbering scheme
    GPIO.setup(BUTTONPINA, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(BUTTONPINB, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(BUTTONPINA, GPIO.FALLING, callback=buttonCallbackA, bouncetime=300)  
    GPIO.add_event_detect(BUTTONPINB, GPIO.FALLING, callback=buttonCallbackB, bouncetime=300)  


#Red button pressed : confirm action
def buttonCallbackA(channel):
    print ("DEBUG: Pressed [A]/[RED] !")

    #if shudown then do shutdown
    if PANELS[currentPanelIdx] == "Shutdown":
        print ("Good night!")
        #os.system("sudo shutdown -h now")
        return


    
#Green button pressed : move to next panel
def buttonCallbackB(channel):
    print ("DEBUG: Pressed [B]/[GREEN] !")
    global currentPanelIdx
    currentPanelIdx = (currentPanelIdx + 1) % len(PANELS)

    #draws the UPDATED  panel
    drawCurrentPanel()


#make a blank image sized for the panel
def makeBlankPanelImage():
    # Display resolution in epd2in13.py
    #EPD_WIDTH       = 128
    #EPD_HEIGHT      = 250

    # For simplicity, the arguments are explicit numerical coordinates
    image = Image.new('1', (epd2in13.EPD_HEIGHT, epd2in13.EPD_WIDTH), 255)  # 255: clear the frame
    #image = Image.new('1', (EPD_HEIGHT, EPD_WIDTH), 255)  # 255: clear the frame
    draw = ImageDraw.Draw(image)

    #Screen is horizontal
    #the TOP LEFT (sticker)  angle is 0,0, BOTTOM RIGHT is max 
    image_width, image_height  = image.size

    return image, draw, image_width, image_height


################################################################################################3
##
##  Draw Weather Panel
##
################################################################################################3
def drawWeatherPanel():

    #make blank image and get all we need to draw
    image, draw, image_width, image_height = makeBlankPanelImage()
    

    wNow = None
    wLater = None
    
    
    try:
        #get current weather
        wNow = getWeatherNow ()

        #now +6h-9h
        wLater = getWeather(2)
    except BaseException,ex:
        #something wrong happened
        traceback.print_exc()
        pass
        

    try:
        #get the image to display
        imgName = "unknown.png" if wNow == None else getImageFromCondition(wNow["status"].lower(), datetime.datetime.now())
        
        imgWeather = Image.open (os.path.join(PATH_TO_IMG,imgName))
    except BaseException,ex:
        #failed to find the image most likey
        traceback.print_exc()
        pass


    ##########################################3
    ##
    ## DRAWING START
    ##
    #horizontal line
    for i in range(5):
        draw.line ([(0, 64+i),( image_width-64 -2*i, 64+i )], fill=0)


    ###########################################3
    ##
    ## TOP PART : WEATHER
    ##
    #the weather in text
    draw.text((PADDING, PADDING), wNow["weather"], font = font_big, fill = 0)
    #weather change
    vWeatherChange = "?"
    if not wLater == None:
        if wNow["status"] == wLater["status"]:
            vWeatherChange = "holding"
        else:
            vWeatherChange = wLater["weather"]
    vWeatherChange = "%s %s (%dc)" % (wLater ["time"][11:16], vWeatherChange, wLater["temp"])
    #temp min-max
    draw.text((PADDING, PADDING + 30), vWeatherChange, font = font_mediumsmall, fill = 0)


    ###########################################3
    ##
    ## BOTTOM PART : Misc info
    ##
    now = datetime.datetime.now()
    draw.text((PADDING, PADDING +60+10), now.strftime("%A"), font = font_medium, fill = 0)
    draw.text((PADDING, PADDING +60+30), now.strftime("%Y/%m/%d"), font = font_small, fill = 0)
    draw.text((PADDING, image_height - 14), now.strftime("Last update  %H:%M"), font = font_xsmall, fill = 0)

    #draw image
    draw.bitmap ( (image_width - 64 - PADDING, 64), imgWeather)

    #draw temp
    draw.text((image_width - 64 - PADDING - 48 -10, 64 + 8), "%2d" % (float(wNow["temp"])), font = font_xbig, fill = 0)
    draw.arc ([(image_width - 64 - 10 -10 , 64 + 12), (image_width - 64 -10 + 8 -10, 64 + 12 + 8)], 0, 360, fill= 0)
    

    # Moon
    #drawMoon()
        
    ###########################################3
    ##
    ## Drawing finished - display
    ##
    img = image.rotate(90)

    #display on e-Ink
    eInkShow(epd, img)



################################################################################################3
##
##  Draw Shutdown Panel
##
################################################################################################3
def drawShutdownPanel():
    print("DEBUG: shut panel")
    #make blank image and get all we need to draw
    image, draw, image_width, image_height = makeBlankPanelImage()

    draw.text (( 12, 24 ), "Shutdown?", font= font_xbig, fill = 0  )  
    draw.text (( 12, 64 ), "Press [RED] button to confirm", font= font_small, fill = 0  )  

    ## Drawing finished - display
    img = image.rotate(90)
    #display on e-Ink
    eInkShow(epd, img)


################################################################################################3
##
##  Draw Others Panel
##
################################################################################################3
def drawOthersPanel():
    print("others panel")
    #make blank image and get all we need to draw
    image, draw, image_width, image_height = makeBlankPanelImage()

    draw.text (( 12, 24 ), "Others...", font= font_xbig, fill = 0  )  
    draw.text (( 12, 64 ), "Current IP: %s" % (alan_utils.getWifiIP()), font= font_small, fill = 0  )  

    ## Drawing finished - display
    img = image.rotate(90)
    #display on e-Ink
    eInkShow(epd, img)


################################################################################################3
##
##  Choose which panel to draw
##
################################################################################################3
def drawCurrentPanel():
    if PANELS[currentPanelIdx] == "Weather":
        drawWeatherPanel()
        return
    elif PANELS[currentPanelIdx] == "Shutdown":
        drawShutdownPanel()
        return
    elif PANELS[currentPanelIdx] == "Others":
        drawOthersPanel()
        return

    #what the hell are we doing here??
    raise ValueError ("Unknown current panel idx : %d" % (currentPanelIdx))
    
    
################################################################################################3
##
##  Main entry point
##
################################################################################################3
if __name__ == '__main__':
    currentPanelIdx = 1

    #init the e-Ink
    epd = eInkInit()

    #init buttons
    initButtons()

    #draws the current panel
    drawCurrentPanel()

    print("Here we go! Press CTRL+C to exit")
    try:
        while 1:
            #print (".")
            time.sleep(1)
            
    except KeyboardInterrupt: # If CTRL+C is pressed, exit cleanly:
        pass
    finally:
        GPIO.cleanup() # cleanup all GPIO
        

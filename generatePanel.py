# coding=UTF-8
#!/usr/bin/python
# -*- coding: UTF-8 -*-
# vim: set fileencoding=UTF-8 :

from PIL import Image,ImageFont,ImageDraw
from resizeimage import resizeimage
import findEmote, utilFunctions
import random, ConfigParser
import praw
from utilFunctions import insertLineBreaks

#charsInLine=22
global panelSize
panelSize=(200,200)
global charHeight
global charHeightCloseup
charHeight=None
charHeightCloseup=None#charHeight*closeupMultiplier
names={}#should mirror generatecomic name dictionary

# set the panel size from another module
def setPS(ps):
	global panelSize
	panelSize=ps
	return ps


config = ConfigParser.ConfigParser()
config.readfp(open('config.cfg'))

fnt = ImageFont.truetype(config.get('Fonts','talk_font'), config.getint('Fonts','talk_size'))
lineHeight = config.getint('Fonts','talk_height')
fontPixelWidth = config.getint('Fonts','talk_charwidth')
closeupMultiplier = config.getfloat('Options','closeup_zoom')

boxBorder=(15,9)
characterMaxSize=(panelSize[0]/2,panelSize[0]/2)

charHeight,charHeightCloseup,farCharHeight=utilFunctions.setPanelSizes(panelSize,closeupMultiplier) # moved to generate comic.py


# draws text, returns how tall the box ended up being
def drawText(image,text,box,arroworientation,color=None):
	if color is None:
		color=(0,0,0,255)
	if len(text)<1:
		return box[1]
	text=insertLineBreaks(text,box[2]/fontPixelWidth)#text.upper()#charsInLine)#
	d = ImageDraw.Draw(image)
	#circle(d,(40,40),10)
	print 'txtcount '+str(text.count('\n')+1)
	if text.count('\n')+1>7:
		print 'TXTCOUNT TOO BIG THINGS WILL BREAK'
	boxHeight=boxBorder[0]+lineHeight*(text.count('\n')+1)
	#d.rectangle((box[0],box[1],box[2],box[1]+boxHeight),fill=(255,255,255),outline=(0,0,0))
	dbox=Image.open("dialoguebubble.png")
	dbox=dbox.resize((box[2],boxHeight))
	image.paste(dbox,(box[0],box[1]),mask=dbox)

	#draw arrow
	arrow=Image.open("bubblearrow.png")
	arrowXMod=None
	if arroworientation==0:
		arrowXMod=box[2]/6
		arrow=arrow.transpose(Image.FLIP_LEFT_RIGHT)
	if arroworientation==1:
		arrowXMod=box[2]/2
	if arroworientation==2:
		arrowXMod=3*box[2]/4
		#arrow=arrow.transpose(Image.FLIP_LEFT_RIGHT)
	print arrowXMod
	print box[2]

	try:
		arrowpos=(box[0]+arrowXMod,box[1]+boxHeight-5)
		arrow=arrow.resize((arrow.size[0],panelSize[1]-charHeight-arrowpos[1]))
		image.paste(arrow,arrowpos,mask=arrow)
	except:
		print 'failed to draw text arrow'
	d.text((box[0]+boxBorder[0],box[1]+boxBorder[1]), text, font=fnt, fill=color)
	return boxHeight

# gets the background image for a panel
# the background is chosen in selectBackground, which is called by processChatLog (both in generateComic.py)
def getBackgroundImage(backgroundName,closeup=False):
	bg=Image.open(backgroundName).convert('RGBA')
	stretch=config.get('Options','squish_image').upper()=='TRUE'

	#bg=imageFlip(bg)
	messup=utilFunctions.getTransformList(7,0)
	print "Transform list "+str(messup)
	bg=utilFunctions.applyTransformList(messup,bg)

	if stretch:
		if closeup:
			distance=int((closeupMultiplier*bg.size[0]-bg.size[0])/2)
			bg=bg.crop((distance,distance*2,bg.size[0]-distance,bg.size[1]))
		bg=bg.resize(panelSize)
	else:
		wX=bg.size[0]
		hY=bg.size[1]
		if wX<panelSize[0] or hY<panelSize[1]:
			resize_constant=2  # 2 is arbitrary, but I don't think we'll be likely to encounter smaller images
			wX=wX*resize_constant
			hY=hY*resize_constant
			bg=bg.resize([wX,hY])

		if closeup:
			bigWidth=int(wX*closeupMultiplier)
			bigHeight=int(hY*closeupMultiplier)
			offX=int(utilFunctions.triangularInt(-wX,wX,0)/closeupMultiplier)/4
			offY=int(utilFunctions.triangularInt(-hY,hY,0)/closeupMultiplier)/4

			left=(bigWidth-wX)/2+offX
			top=(bigHeight-hY)/2+offY
			right=(bigWidth+wX)/2+offX
			bottom=(bigHeight+hY)/2+offY

			bg=bg.resize([bigWidth,bigHeight])
			bg=bg.crop((left,top,right,bottom))
		bg=resizeimage.resize_cover(bg,panelSize)

	filter=Image.new('RGBA',bg.size,color=(255,255,255,128))
	bg=Image.composite(bg,filter,filter)
	if not utilFunctions.rollOdds(420): #1/420 odds of a transformed background gives around a 1.18% chance that any given comic contains a transformed panel background
		bg=utilFunctions.undoTransformList(messup,bg)
	return bg

#
def getCharacterImage(name1,dialog1,transpose,imheight=None):
	im=None
	if name1 in names:
		print 'getting image from manual list for '+str(name1)+" "+names[name1]
		im=findEmote.getRandomEmote(dialog1,names[name1])
	else:
		print 'getting image from procedural for '+str(name1)
		im=findEmote.getProceduralEmote(name1,dialog1)#Image.open("flair.png").convert('RGBA')
	im.thumbnail(characterMaxSize)
	#print 'gci imheight '+str(imheight)
	if imheight is None:
		imheight=charHeight#3*panelSize[1]/8
	imheightold=imheight
	if im.size[0]>imheight:
		imheight=imheight*(im.size[0]/im.size[1])
		print 'too long resizing image '+str(charHeight)+" "+str(imheightold)
	im=im.resize(( # the max functions are to handle any bugged-out emotes
		max(int(imheight*(float(im.size[0])/im.size[1])),1),
		max(int(imheight),1)))
	if transpose:
		im=im.transpose(Image.FLIP_LEFT_RIGHT)
	return im

#
def hasRoomForDialogue3(dialog1,dialog2,dialog3):
	lines1=insertLineBreaks(dialog1,getBubbleLength()/fontPixelWidth).count('\n')+1
	lines2=insertLineBreaks(dialog2,getBubbleLength()/fontPixelWidth).count('\n')+1
	lines3=insertLineBreaks(dialog3,getBubbleLength()/fontPixelWidth).count('\n')+1
	print 'hasroomfordialogue numlines '+str(lines1+lines2+lines3)
	totalLines=lines1+lines2+lines3
	if panelSize[1]<201:
		return totalLines<4
	if panelSize[1]<301:
		return totalLines<8
	if panelSize[1]<401:
		return totalLines<13

#
def hasRoomForDialogue2(dialog1,dialog2):
	lines1=insertLineBreaks(dialog1,getBubbleLength()/fontPixelWidth).count('\n')+1
	lines2=insertLineBreaks(dialog2,getBubbleLength()/fontPixelWidth).count('\n')+1
	print 'hasroomfordialogue numlines '+str(lines1+lines2)
	totalLines=lines1+lines2
	if panelSize[1]<201:
		return totalLines<5
	if panelSize[1]<301:
		return totalLines<11
	if panelSize[1]<401:
		return totalLines<15
spaceFromEdge=[5,5]

#
def getBubbleLength():
	return 2*panelSize[0]/3

# doesn't zoom in on characters when closeup to help them fit
def draw3CharactersAndBackground(name1,name2,name3,dialog1,dialog2,dialog3,backgroundName,closeup=True):
	bg=getBackgroundImage(backgroundName,closeup)
	im=None
	heightUsed=farCharHeight
	if closeup and charHeightCloseup is not None:
		heightUsed=charHeightCloseup
	im=getCharacterImage(name1,dialog1,True,heightUsed)
	posx=5
	posy=panelSize[1]-im.size[1]
	if closeup:
		posy=panelSize[1]-heightUsed#int(heightUsed/closeupMultiplier)#charHeight#
	box=(posx,posy,posx+im.size[0],posy+im.size[1])
	bg.paste(im,box,mask=im)

	im2=getCharacterImage(name2,dialog2,False,heightUsed)
	posx=panelSize[0]-5-im2.size[0]
	#posy=panelSize[1]-im2.size[1]
	box=(posx,posy,posx+im2.size[0],posy+im2.size[1])
	bg.paste(im2,box,mask=im2)

	im3=getCharacterImage(name3,dialog3,False,heightUsed)
	posx=panelSize[0]/2-im2.size[0]/2
	#posy=panelSize[1]-im2.size[1]
	box=(posx,posy,posx+im3.size[0],posy+im3.size[1])
	bg.paste(im3,box,mask=im3)

	return bg

# try to make a generic character drawing
# list is a dictionary in the form of {Name1:Dialogue1,Name2:Dialogue2,etc…}
def putCharactersOnBackground(list,backgroundName,closeup=True):
	bg=getBackgroundImage(backgroundName,closeup)
	im=None
	heightUsed=farCharHeight
	if closeup:
		heightUsed=charHeight
	for name in list.keys():
		im=getCharacterImage(name,list[name],False,heightUsed)
		posy=panelSize[1]-im.size[1]
		#posx+=

#
def draw2CharactersAndBackground(name1,name2,dialog1,dialog2,backgroundName,closeup=True):
	bg=getBackgroundImage(backgroundName,closeup)
	im=None
	heightUsed=farCharHeight
	if closeup:
		heightUsed=charHeight
	im=getCharacterImage(name1,dialog1,True,heightUsed)
	posx=25
	posy=panelSize[1]-im.size[1]
	if closeup:
		posy=panelSize[1]-charHeight#
	box=(posx,posy,posx+im.size[0],posy+im.size[1])
	bg.paste(im,box,mask=im)


	im2=getCharacterImage(name2,dialog2,False,heightUsed)
	posx=panelSize[0]-25-im2.size[0]
	#posy=panelSize[1]-im2.size[1]
	box=(posx,posy,posx+im2.size[0],posy+im2.size[1])
	bg.paste(im2,box,mask=im2)
	return bg

#
def draw1CharacterAndBackground(name1,dialog1,backgroundName,closeup=True):
	bg=getBackgroundImage(backgroundName,closeup)
	heightUsed=farCharHeight
	if closeup:
		heightUsed=charHeight
	im=getCharacterImage(name1,dialog1,True,heightUsed)
	posx=panelSize[0]/2-im.size[0]/2
	posy=panelSize[1]-im.size[1]
	if closeup:
		posy=panelSize[1]-charHeight#
	box=(posx,posy,posx+im.size[0],posy+im.size[1])
	bg.paste(im,box,mask=im)
	return bg

#
def drawLeftText(bg,dialog1,height,col=None):
	bubbleLength=getBubbleLength()
	return drawText(bg,dialog1,(spaceFromEdge[0],height,bubbleLength),0,color=col)

#
def drawRightText(bg,dialog1,height,col=None):
	bubbleLength=getBubbleLength()
	return drawText(bg,dialog1,(spaceFromEdge[0]+2*bubbleLength/5,height,bubbleLength),2,color=col)

#
def drawCenterText(bg,dialog1,height,col=None):
	bubbleLength=getBubbleLength()
	return drawText(bg,dialog1,(spaceFromEdge[0]+1*bubbleLength/6,height,int(bubbleLength*1.2)),1,color=col)

#
def drawBorder(img):
	d = ImageDraw.Draw(img)
	d.line((0,0, img.size[0],0), fill=(0,0,0),width=5)
	d.line((0,0,0,img.size[1]), fill=(0,0,0),width=5)
	d.line((0,img.size[1],img.size[0],img.size[1]), fill=(0,0,0),width=5)
	d.line((img.size[0],img.size[1], img.size[0],0), fill=(0,0,0),width=5)
	return img

# 2 characters both with dialogue
def drawPanel3Characters(name1,name2,name3,dialog1,dialog2,dialog3,backgroundName,textOrder=0,iscloseup=False):
	bg=draw3CharactersAndBackground(name1,name2,name3,dialog1,dialog2,dialog3,backgroundName,closeup=iscloseup)
	text2height=None
	if textOrder==0:
		text1height=drawLeftText(bg,dialog1,spaceFromEdge[1])
		text2height=drawRightText(bg,dialog2,text1height+2*spaceFromEdge[1])
	if textOrder==1:
		text1height=drawRightText(bg,dialog1,spaceFromEdge[1])
		text2height=drawLeftText(bg,dialog2,text1height+2*spaceFromEdge[1])
	drawCenterText(bg,dialog3,text2height+text1height+3*spaceFromEdge[1])
	drawBorder(bg)
	return bg

# 2 characters both with dialogue
def drawPanel2Characters(name1,name2,dialog1,dialog2,backgroundName,textOrder=0,iscloseup=False):
	bg=draw2CharactersAndBackground(name1,name2,dialog1,dialog2,backgroundName,closeup=iscloseup)
	if textOrder==0:
		text1height=drawLeftText(bg,dialog1,spaceFromEdge[1])
		drawRightText(bg,dialog2,text1height+2*spaceFromEdge[1])
	if textOrder==1:
		text1height=drawRightText(bg,dialog1,spaceFromEdge[1])
		drawLeftText(bg,dialog2,text1height+2*spaceFromEdge[1])
	drawBorder(bg)
	return bg#bg.save("test.jpg","JPEG")

# one character
def drawPanel1Character(name1,dialog1,backgroundName,iscloseup=False):
	bg=draw1CharacterAndBackground(name1,dialog1,backgroundName,closeup=iscloseup)
	drawCenterText(bg,dialog1,spaceFromEdge[1])
	drawBorder(bg)
	return bg#bg.save("test.jpg","JPEG")

# empty panel
def drawPanelNoDialogue(names,backgroundName,seed,iscloseup=False):
	if len(names)==1:
		return drawBorder(draw1CharacterAndBackground(names[0],names[0]+seed,backgroundName,iscloseup))
	if len(names)==2:
		return drawBorder(draw2CharactersAndBackground(names[0],names[1],names[0]+seed,names[1]+seed,backgroundName,iscloseup))
	if len(names)==3:
		return drawBorder(draw3CharactersAndBackground(names[0],names[1],names[2],names[0]+seed,names[1]+seed,names[2]+seed,backgroundName,iscloseup))
	return drawBorder(getBackgroundImage(backgroundName,False))



# Old test code???

#drawPanel1("someone3","someoneelse","i invited darqwolff why did that happen","smaller text whaat does it look like","backgrounds/puffBg.jpg")
#drawPanel1Character("eoitruroi","tfw plounge has a discord","backgrounds/puffBg.jpg",iscloseup=True)
# bg=drawPanel3Characters("someobne3","somewoneelse","person3","so it fits like fuck","i invitted darqwolff","smallerrr text ","backgrounds/puffBg.jpg",textOrder=0,iscloseup=False)
# dialog1="but usuually at the same time you dont want to drink too fresh coffee"
# dialog2="testing text here lots orf text omg srthiorstjh hburisthuj bneruiiugerhg itrouih more text more add more text Lorem ipsum dolor sit amet, consectetur adipiscing elit,"
# print 'has room for dialogue '+str(hasRoomForDialogue2(dialog1,dialog2))
# #drawPanel2Characters("someone3","someoneelse",dialog1,dialog2,"backgrounds/puffBg.jpg")
# bg.save("test.jpg","JPEG")
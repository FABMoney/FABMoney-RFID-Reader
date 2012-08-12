#
# FABMoney 0.3
#
# Author: Massimo Menichinelli
# Website:
# http://fabmoney.org
# http://openp2pdesign.org
#
# License: MIT License
#

import os
import wx
import sys
import networkx as nx
import matplotlib.pyplot as plt
import datetime
import glob
import wx.lib.mixins.listctrl  as  listmix
import pickle
import serial
import time
import random
import csv

class Transaction(object):
    def __init__(self, sender, receiver, timestamp, where):
        self.sender = sender
        self.receiver = receiver
        self.timestamp = timestamp
        self.where = where

    def create(self):
        self.flow = { self.sender : self.receiver }
        print "The transaction is:",self.flow
        return self.flow

class User(object):
    def __init__(self, username, rfidtag, name, surname, email):
        self.username = username
        self.rfidtag = rfidtag
        self.name = name
        self.surname = surname
        self.email = email


# Initializing variables and the log file
FABMoneyVersion = "0.3"
MyLocalFabLab = "Aalto FabLab"
logmessage = ""
loglist = []
logfile = "FABMoney_log.txt"
FILE = open(logfile,"w")
REFRESH_INTERVAL_MS = 90

all_transactions = []
transactionsdb = "FABMoney_transactions.pkl"
all_user_data = []
usersdb = "FABMoney_user_data.pkl"
graphfile = "FABMoney_network.gexf"

transactionsmultidigraph = nx.MultiDiGraph()
# Matplotlib won't visualize Multidigraph (parallel edges)
# so we save the .gexf file as Multidigraph (for further investigation with Gephi)
# So the visualization in the program is not the best way for understanding the network...


def savegexfwithstyle(graph, filename):
    nx.write_gexf(graph, filename)
    o = open("tmp.gexf","w")
    for line in open(filename):
        line = line.replace("<ns0:","<viz:")
        o.write(line)
    o.close()
    os.rename("tmp.gexf",filename)
    print "saved"
    # Fixing the bug in writing the style of the .gexf file


def hex_to_rgb(value):
    # Color conversion for the graoh nodes
    value = value.lstrip('#')
    lv = len(value)
    return tuple(int(value[i:i+lv/3], 16) for i in range(0, lv, lv/3))

def rgb_to_hex(rgb):
    # Color conversion for the graoh nodes
    return '#%02x%02x%02x' % rgb

def ScanSerialPorts():
    # scan for available ports. return a list of device names.
    return glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyS*') + glob.glob('/dev/ttyUSB*')

class RedirectText(object):
    # Redirect the print message to the Status log area
    def __init__(self,aWxTextCtrl):
        self.out=aWxTextCtrl

    def write(self,string):
        self.out.WriteText(string)
     
class EditableListCtrl(wx.ListCtrl, listmix.TextEditMixin):
    # Editable list control of the users
    def __init__(self, parent, ID=wx.ID_ANY, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.TextEditMixin.__init__(self)
 

class UsersList(wx.Dialog):
    def __init__(self, parent, id, title):
        # Look for the file and launch a warning dialog if it does not exist
        global all_user_data
          
        wx.Dialog.__init__(self, parent, id, title="Users List", size=(800,500))

        self.list_ctrl = EditableListCtrl(self, size=(750,450),style=wx.LC_REPORT | wx.RAISED_BORDER)
        self.index = 0
 
        self.list_ctrl.InsertColumn(0, "Username",width=150)
        self.list_ctrl.InsertColumn(1, "RFID Tag",width=150)
        self.list_ctrl.InsertColumn(2, "Name",width=150)
        self.list_ctrl.InsertColumn(3, "Surname",width=150)
        self.list_ctrl.InsertColumn(4, "E-mail",width=150)
     
        AddLineButton = wx.Button(self, 1, 'Add a new user')
        AddLineButton.Bind(wx.EVT_BUTTON, self.AddLine)
        SaveButton = wx.Button(self, 2, 'Save')
        SaveButton.Bind(wx.EVT_BUTTON, self.OnSaveDB)
        CloseButton = wx.Button(self, 3, 'Close')
        CloseButton.Bind(wx.EVT_BUTTON, self.OnClose)
 
        index = 0
        for i in range(len(all_user_data)):
            self.list_ctrl.InsertStringItem(index, all_user_data[i].username)
            self.list_ctrl.SetStringItem(index, 1, all_user_data[i].rfidtag)
            self.list_ctrl.SetStringItem(index, 2, all_user_data[i].name)
            self.list_ctrl.SetStringItem(index, 3, all_user_data[i].surname)
            self.list_ctrl.SetStringItem(index, 4, all_user_data[i].email)
            index += 1
         
 
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.list_ctrl, 0, wx.ALL|wx.EXPAND, 5)
        sizerbuttons = wx.BoxSizer(wx.HORIZONTAL)
        sizerbuttons.Add(AddLineButton, 0, wx.ALL|wx.CENTER, 5)
        sizerbuttons.Add(SaveButton,0,wx.ALL|wx.ALIGN_RIGHT, 5)
        sizerbuttons.Add(CloseButton,0,wx.ALL|wx.ALIGN_RIGHT, 5)
        sizer.Add(sizerbuttons, 0, wx.ALIGN_RIGHT, 5)

        self.SetSizer(sizer)
     
    def AddLine(self, event):
        line = "Username %s" % self.index
        self.list_ctrl.InsertStringItem(self.index, line)
        self.list_ctrl.SetStringItem(self.index, 1, "RFID Tag")
        self.list_ctrl.SetStringItem(self.index, 2, "Name")
        self.list_ctrl.SetStringItem(self.index, 3, "Surname")
        self.list_ctrl.SetStringItem(self.index, 4, "E-mail")
        self.index += 1
        lastadded = User("Username", "RFID Tag", "Name", "Surname", "E-mail")
        all_user_data.append(lastadded)
     
     
    def OnMessage(self, title,content):
        dlg = wx.MessageDialog(self, content, title, wx.OK|wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()
 
    def OnSaveDB(self, event):
        global all_user_data
        writingdb = open(usersdb, 'wb')

        for row in range(self.list_ctrl.GetItemCount()):
            all_user_data[row].username = self.list_ctrl.GetItem(row, 0).GetText()
            all_user_data[row].rfidtag = self.list_ctrl.GetItem(row, 1).GetText()
            all_user_data[row].name = self.list_ctrl.GetItem(row, 2).GetText()
            all_user_data[row].surname = self.list_ctrl.GetItem(row, 3).GetText()
            all_user_data[row].email = self.list_ctrl.GetItem(row, 4).GetText()
           
        pickle.dump(all_user_data, writingdb)
        writingdb.close()
        dlg = wx.MessageDialog(self, "Database saved succesfully!", "Saving...", wx.OK|wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()
     
    def OnClose(self, event):
        self.Close(True)
       

class TransactionsList(wx.Dialog):
    def __init__(self, parent, id, title):
        # Look for the file and launch a warning dialog if it does not exist
        global all_user_data
        global all_transactions
        global transactionsdb
          
        wx.Dialog.__init__(self, parent, id, title="Transactions List", size=(650,500))

        self.list_ctrl = wx.ListCtrl(self, size=(750,450),style=wx.LC_REPORT | wx.RAISED_BORDER)
        self.index = 0
 
        self.list_ctrl.InsertColumn(0, "Sender",width=150)
        self.list_ctrl.InsertColumn(1, "Receiver",width=150)
        self.list_ctrl.InsertColumn(2, "When",width=150)
        self.list_ctrl.InsertColumn(3, "Where",width=150)
     
        SaveCSVButton = wx.Button(self, 1, 'Save a .csv file')
        SaveCSVButton.Bind(wx.EVT_BUTTON, self.OnSaveCSV)
        CloseButton = wx.Button(self, 2, 'Close')
        CloseButton.Bind(wx.EVT_BUTTON, self.OnClose)
 
        index = 0
        for i in range(len(all_transactions)):
            self.list_ctrl.InsertStringItem(index, all_transactions[i].sender)
            self.list_ctrl.SetStringItem(index, 1, all_transactions[i].receiver)
            self.list_ctrl.SetStringItem(index, 2, all_transactions[i].timestamp)
            self.list_ctrl.SetStringItem(index, 3, all_transactions[i].where)
            index += 1
         
 
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.list_ctrl, 0, wx.ALL|wx.EXPAND, 5)
        sizerbuttons = wx.BoxSizer(wx.HORIZONTAL)
        sizerbuttons.Add(SaveCSVButton,0,wx.ALL|wx.ALIGN_RIGHT, 5)
        sizerbuttons.Add(CloseButton,0,wx.ALL|wx.ALIGN_RIGHT, 5)
        sizer.Add(sizerbuttons, 0, wx.ALIGN_RIGHT, 5)

        self.SetSizer(sizer)
     
     
    def OnMessage(self, title,content):
        dlg = wx.MessageDialog(self, content, title, wx.OK|wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()
 
    def OnSaveCSV(self, event):
        global all_user_data
        global all_transactions
       
        file_choices = "CSV (*.csv)|*.csv"
     
        dlg = wx.FileDialog(
            self,
            message="Save transactions as...",
            defaultDir=os.getcwd(),
            defaultFile="FABMoney_transactions.csv",
            wildcard=file_choices,
            style=wx.SAVE)
     
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            out = csv.writer(open(path,"w"), delimiter=',',quoting=csv.QUOTE_ALL)
            out.writerow(all_transactions)
       
        dlg = wx.MessageDialog(self, "Transactions saved succesfully!", "Saving...", wx.OK|wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()
     
    def OnClose(self, event):
        self.Close(True)


class MainWindow(wx.Frame):
    def __init__(self, parent, title, serialport, serialreading):
        noResize_frameStyle = wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER
        wx.Frame.__init__(self, parent, title=title, size=(900,700), style=noResize_frameStyle)
        self.SetIcon(wx.Icon('images/fabmoney-icon.png', wx.BITMAP_TYPE_PNG)) # Icon of the program, not working now
        self.CreateStatusBar() # A StatusBar in the bottom of the window
        self.serialport = serialport
        self.serialreading = serialreading
        global all_transactions
        global all_user_data
        global transactionsmultidigraph
        global graphfile
       
        bSizer1 = wx.BoxSizer( wx.VERTICAL )
     
        fgSizer2 = wx.FlexGridSizer( 3, 1, 0, 0 )
        fgSizer2.SetFlexibleDirection( wx.BOTH )
        fgSizer2.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )
     
        self.m_panel5 = wx.Panel( self, wx.ID_ANY, wx.DefaultPosition, wx.Size( 900,70 ), wx.NO_BORDER|wx.TAB_TRAVERSAL )
        fgSizer2.Add( self.m_panel5, 1, wx.EXPAND |wx.ALL, 0 )
     
        self.m_panel5.bitmap = wx.Bitmap('images/fabmoney-header.png')
        wx.EVT_PAINT(self.m_panel5, self.HeaderPaint)
     
        self.m_panel6 = wx.Panel( self, wx.ID_ANY, wx.DefaultPosition, wx.Size( 900,500 ), wx.RAISED_BORDER|wx.TAB_TRAVERSAL )
        fgSizer2.Add( self.m_panel6, 1, wx.EXPAND |wx.ALL, 0 )
     
        self.m_panel6.bitmap = wx.Bitmap('FABMoney_current_network.png')
        wx.EVT_PAINT(self.m_panel6, self.NetworkPaint)
     
        self.m_panel7 = wx.Panel( self, wx.ID_ANY, wx.DefaultPosition, wx.Size( 900,108 ), wx.NO_BORDER|wx.TAB_TRAVERSAL )
        fgSizer2.Add( self.m_panel7, 1, wx.EXPAND |wx.ALL, 2 )
     
        log = wx.TextCtrl(self.m_panel7, wx.ID_ANY, size=(900,100),
                          style = wx.TE_MULTILINE|wx.TE_READONLY|wx.VSCROLL)
     
        # Starting the log
        # Redirect text here
        redir=RedirectText(log)
        sys.stdout=redir
        # Starting the log, and writing it to the file
        now = datetime.datetime.now()
        logmessage = "Welcome to FABMoney v."+FABMoneyVersion
        loglist.append(logmessage)
        print logmessage
        FILE.write(logmessage+"\n")
        logmessage = "Current time: "+now.strftime("%Y-%m-%d %H:%M")
        loglist.append(logmessage)
        print logmessage
        FILE.write(logmessage+"\n")
        logmessage = "Ready to work"
        loglist.append(logmessage)
        print logmessage
        FILE.write(logmessage+"\n")
        logmessage = "..."
        loglist.append(logmessage)
        print logmessage
        FILE.write(logmessage+"\n")
     
     
     
        # Log: check this two ways:
        # http://stackoverflow.com/questions/5493984/how-to-make-something-like-a-log-box-in-wxpython
        # http://www.blog.pythonlibrary.org/2009/01/01/wxpython-redirecting-stdout-stderr/
     
        bSizer1.Add( fgSizer2, 1, wx.EXPAND, 5 )
     
        self.SetSizer( bSizer1 )
        self.Layout()

        # Setting up the menu.
        filemenu= wx.Menu()
        settingsmenu= wx.Menu()

        # wx.ID_ABOUT and wx.ID_EXIT are standard ids provided by wxWidgets.
        menuSaveImage = filemenu.Append(wx.ID_SAVE,"Save an Image"," Save an image of the network")
        menuSaveNetwork = filemenu.Append(wx.ID_ANY,"Save the Network"," Save the GEXF file of the network")
        menuSaveLog = filemenu.Append(wx.ID_ANY,"Save the Log"," Save a text file of the transactions in the network")
        menuExit = filemenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")
     
        # Menu items for the settings
        menuSettings = settingsmenu.Append(wx.ID_ANY,"Port S&ettings"," Settings for FABMoney")
        menuUsers = settingsmenu.Append(wx.ID_ANY,"U&sers"," Users and their RFID tag for FABMoney")
        menuTransactions = settingsmenu.Append(wx.ID_ANY,"T&ransactions"," Check all the transactions and export them")
        menuAbout = settingsmenu.Append(wx.ID_ABOUT, "&About"," Information about FABMoney v."+FABMoneyVersion)

        # Creating the menubar.
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu,"&File") # Adding the "filemenu" to the MenuBar
        menuBar.Append(settingsmenu,"&Setting") # Adding the "settingsmenu" to the MenuBar
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.

        # Set events for the Menu
        self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
        self.Bind(wx.EVT_MENU, self.OnChooseSerialPort, menuSettings)
        self.Bind(wx.EVT_MENU, self.OnUsers, menuUsers)
        self.Bind(wx.EVT_MENU, self.OnTransactions, menuTransactions)
        self.Bind(wx.EVT_MENU, self.OnExit, menuExit)
        self.Bind(wx.EVT_MENU, self.OnSaveImage, menuSaveImage)
        self.Bind(wx.EVT_MENU, self.OnSaveNetwork, menuSaveNetwork)
        self.Bind(wx.EVT_MENU, self.OnSaveLog, menuSaveLog)

        self.Show(True)
       
        # Check if the users database exists
        try:
            with open(usersdb) as f: pass
        except IOError as e:
            print "ERROR: No user data database file found! You can create a new one now."
            self.OnMessage("ERROR", "No user data database file found! You can create a new one now.")
            self.OnUsers(e)
        else:
            readingdb = open(usersdb, 'rb')
            all_user_data = pickle.load(readingdb)
            print "Reading the users details..."
            readingdb.close()
       
        # Check if the db of the transactions is present or not
        try:
            with open(transactionsdb) as f: pass
        except IOError as e:
            print "ERROR: No transactions database file found! En empty one will be created now."
            self.OnMessage("ERROR", "No transactions database file found! En empty one will be created now.")
            all_transactions = []
            writingdb = open(transactionsdb, 'wb')
            pickle.dump(all_transactions, writingdb)
            writingdb.close()
        else:
            readingdb = open(transactionsdb, 'rb')
            all_transactions = pickle.load(readingdb)
            print "Reading the transactions details..."
            readingdb.close()
           
        # Check if the graph of the transactions is present or not
        try:
            with open(graphfile) as f: pass
        except IOError as e:
            print "ERROR: No transactions network file found! En empty one will be created now."
            self.OnMessage("ERROR", "No transactions graph file found! En empty one will be created now.")
            transactionsmultidigraph = nx.MultiDiGraph()
            savegexfwithstyle(transactionsmultidigraph, graphfile)
        else:
            transactionsmultidigraph = nx.read_gexf(graphfile)
            print "Reading the transactions graph..."
     
        self.OnChooseSerialPort(None)
        # Open the "Choose a Serial Port" dialog at soon as the program is launched
       
        self.serialreading = serial.Serial(self.serialport, 9600)
        time.sleep(1.5)       
      
        self.redraw_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_redraw_timer, self.redraw_timer)
        self.redraw_timer.Start(REFRESH_INTERVAL_MS)
        # Bind the reading of the serial data to a timer, in order to keep reading it
 
    def OnMessage(self, title,content):
        dlg = wx.MessageDialog(self, content, title, wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()
     
    def on_redraw_timer(self, event):
        global all_user_data
        global all_transactions
        global transactionsmultidigraph
        global graphfile
       
        # Reading the serial data from here

        self.serialreading.write('ReadRFID')          
        try:
            MessageFromDevice = self.serialreading.readline().decode('utf-8')[:-2]
        except UnicodeDecodeError, err:
            print "Error reading the device, but going on..."
        else:
            print "Message from the device:", MessageFromDevice

        if MessageFromDevice.find("RFID_read:") != -1:
            print
            value = MessageFromDevice.split(': ')
            RFIDvalue = str(value[1])
            RFIDtocheck = [RFIDvalue]
            print "-------------------------------------------------------------------"
            print "RFID Tag value read:", RFIDvalue
            print "Transaction process started..."
            # Check if the RFID tag is associated to any existing user

            userexists = False
            for user in range(len(all_user_data)):
                if RFIDtocheck == all_user_data[user].rfidtag:
                    userexists = True
                    # The RFID tag has been found in the database
                else:
                    userexists = False
                    # Sorry, no RFID tag found in the database
            if userexists:
                print "The RFID tag exists in the database."
                self.serialreading.write('Hello Sender')
            else:
                self.serialreading.write('Error')
                print "No user is using this RFID tag, please create a specific user or try again!"
                self.OnMessage(title="Process", content="ERROR! No user is using the RFID tag "+RFIDvalue+". Please check or create a user!")
                print
                return
            for user in range(len(all_user_data)):
                if RFIDvalue == all_user_data[user].rfidtag:
                    print "Username found:", all_user_data[user].username,"uses the",RFIDvalue,"RFID tag."
                    Sender = all_user_data[user].username
                    self.serialreading.write('Remove Tag Sender')
                    print 'Please remove your tag, sender.'
                    self.OnMessage(title="Process", content="Dear sender, your RFID tag has been read, please remove it from the device in order to go on with the transaction.")
                    #Fire the LED for Remove Tag Sender
                    self.serialreading.write('ReadRFID')              
                    try:
                        MessageFromDevice2 = self.serialreading.readline().decode('utf-8')[:-2]
                    except UnicodeDecodeError, err:
                        print "Error reading the device, but going on..."
                    else:
                        print "Message from the device:", MessageFromDevice2
                 
                    value2 = MessageFromDevice2.split(': ')
                    RFIDvalue2 = str(value2[1])
                    RFIDtocheck2 = [RFIDvalue2]
                    print "RFID Tag value read:", RFIDvalue2
                    userexists2 = False
                    for user2 in range(len(all_user_data)):
                        if RFIDtocheck2 == all_user_data[user2].rfidtag:
                            userexists2 = True
                            # The RFID tag has been found in the database
                        else:
                            userexists2 = False
                            # Sorry, no RFID tag found in the database
                    if userexists2:
                        print "The RFID tag exists in the database"
                        self.serialreading.write('Hello Receiver')
                    else:
                        self.serialreading.write('Error')
                        print "No user is using this RFID tag, please create a specific user or try again!"
                        self.OnMessage(title="Process", content="ERROR! No user is using the RFID tag "+RFIDvalue2+". Please check or create a user!")
                        return

                    for user2 in range(len(all_user_data)):
                        # Find the user associated with the new RFID tag value
                        if RFIDvalue2 == all_user_data[user2].rfidtag:
                            # Check that the associated user is not the same sender (he/she would then give some FABMoney to himself/herself!)
                            print "Username found:", all_user_data[user2].username,"uses the",RFIDvalue2,"RFID tag."
                            if RFIDvalue2 == RFIDvalue:
                                self.serialreading.write('Error')
                                print "ERROR:", all_user_data[user2].username,'and',Sender,'are the same user.'
                                self.OnMessage(title="Process", content="Error!! Both users are the same!")
                                return
                            else:
                                # Fire the Led for Remove Tag Receiver
                                self.serialreading.write('Remove Tag Receiver')
                                print 'Please remove your tag, receiver.'
                                Receiver = all_user_data[user2].username
                                self.OnMessage(title="Process", content="Dear receiver, your RFID tag has been read, please remove it from the device in order to go on with the transaction.")
                              
                             
                                # Create the transaction here
                                self.serialreading.write('Success')
                                now = datetime.datetime.now()
                                transactiontime = now.strftime("%Y-%m-%d %H:%M")   
                                all_transactions.append(Transaction(Sender,Receiver,transactiontime,MyLocalFabLab))
                                # Saving a transaction
                               
                                transactionsmultidigraph.add_edge(Sender,Receiver,weight=1)
                                # Adding it to the graph
                               
                                self.GraphDrawing
                                print "Transaction successful!"
                                self.OnMessage(title="Process", content="Transaction successfull!")
                                self.SetStatusText("Network of the transactions updated.")
                                print "Network of the transactions updated."                          
                            print "-------------------------------------------------------------------"
     
    def OnChooseSerialPort(self, event):
        # looks for available serial ports
        SerialPortsAvailable = ScanSerialPorts()
        global SerialPortInUse
        # Global variable that can be accessed by the whole program
        dlg = wx.SingleChoiceDialog(self, 'Choose the serial port your FABMoney device is currently using: ', 'Serial port settings', SerialPortsAvailable, wx.CHOICEDLG_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            SerialPortInUse = dlg.GetStringSelection()
            self.serialport = dlg.GetStringSelection()
            logmessage = 'The serial port of the FABMoney device is currently: '+SerialPortInUse
            loglist.append(logmessage)
            self.SetStatusText(logmessage)     
            # assign the new port to the global variable
            print logmessage
            FILE.write(logmessage+"\n")
        dlg.Destroy()
        #start reading data
     
    def GraphDrawing(self):
        # draw the graph of the interactions
        global transactionsmultidigraph
       
        pos=nx.spring_layout(transactionsmultidigraph)
       
        for x in transactionsmultidigraph:
            color_r = random.randrange(0,255)
            color_g = random.randrange(0,255)
            color_b = random.randrange(0,255)
            color_hex = rgb_to_hex((color_r,color_g,color_b))
            node_size = transactionsmultidigraph.degree(x)
            #assign a rgb color for the .gexf file and an converting it to hex for matplotlib
           
            transactionsmultidigraph.node[x]['viz'] = {
                                  "size":node_size,
                                  "color": {"r":color_r,"g":color_g,"b":color_b},
                                  "position": {"x":pos[x][1],"y":[x][0],"z":0}}
            nx.draw_networkx_nodes(transactionsmultidigraph,
                                   pos,
                                   nodelist=[x],
                                   node_color=color_hex,
                                   node_size=transactionsmultidigraph.degree(x)*10,
                                   with_labels=True)
            nx.draw_networkx_edges(transactionsmultidigraph,pos,edge_color='#7E7E80',arrows=True,width=1)
       
        plt.axis('off')
        plt.savefig('FABMoney_current_network.png', transparent=True)
        self.NetworkPaint(None)

     
    def NetworkPaint(self, event):
        dc = wx.PaintDC(self.m_panel6)
        dc.DrawBitmap(self.m_panel6.bitmap, 0, 0)
     
    def HeaderPaint(self, event):
        dc = wx.PaintDC(self.m_panel5)
        dc.DrawBitmap(self.m_panel5.bitmap, 0, 0)

    def OnAbout(self,e):
        # A message dialog box with an OK button. wx.OK is a standard ID in wxWidgets.
        dlg = wx.MessageDialog( self, "A digital and open source currency for collaboration in FabLabs.\nhttp://www.fabmoney.org", "About FABMoney v."+FABMoneyVersion, wx.OK)
        dlg.ShowModal() # Show it
        dlg.Destroy() # finally destroy it when finished.
     
    def OnUsers(self,e):
        dlg = UsersList(self, -1, 'Users List')
        dlg.ShowModal()
        dlg.Destroy()
       
    def OnTransactions(self,e):
        dlg = TransactionsList(self, -1, 'Transactions List')
        dlg.ShowModal()
        dlg.Destroy()
     
    def OnSaveImage(self, event):
        file_choices = "PNG (*.png)|*.png"
     
        dlg = wx.FileDialog(
            self,
            message="Save image as...",
            defaultDir=os.getcwd(),
            defaultFile="FABMoney_network.png",
            wildcard=file_choices,
            style=wx.SAVE)
     
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            #self.canvas.print_figure(path, dpi=self.dpi)
            self.canvas.print_figure(path, dpi=600)
            self.SetStatusText("Saved to %s" % path)
         
    def OnSaveNetwork(self, event):
        global transactionsmultidigraph
        file_choices = "GEXF (*.gexf)|*.gexf"
        dlg = wx.FileDialog(
            self,
            message="Save network as...",
            defaultDir=os.getcwd(),
            defaultFile="FABMoney_network.gexf",
            wildcard=file_choices,
            style=wx.SAVE)
     
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath() 
            savegexfwithstyle(transactionsmultidigraph, dlg.GetPath())
            self.SetStatusText("Saved to %s" % path)
 
    def OnSaveLog(self, event):
        file_choices = "TEXT (*.txt)|*.txt"
        save_dlg = wx.FileDialog(
            self,
            message="Save log as...",
            defaultDir=os.getcwd(),
            defaultFile="FABMoney_log.txt",
            wildcard=file_choices,
            style=wx.SAVE)
     
        dir = os.getcwd()
        if save_dlg.ShowModal() == wx.ID_OK:
            path = save_dlg.GetPath()
            try:
                file = open(path, 'w')
                for item in loglist:
                    print>>file, item
                file.close()
                self.last_name_saved = os.path.basename(path)
                self.SetStatusText("Saved to %s" % path)

            except IOError, error:
                dlg = wx.MessageDialog(self, 'Error saving file\n' + str(error))
                dlg.ShowModal()
        save_dlg.Destroy()


    def OnExit(self,e):
        self.Close(True)  # Close the frame.


if __name__ == '__main__':
   
    # Starting the app
    print "FABMoney v."+FABMoneyVersion
    print "Starting the program..."
    print
   
    app = wx.App(False)
    frame = MainWindow(None, "FABMoney v."+FABMoneyVersion+" - Desktop app", None, None)
    app.MainLoop()
    FILE.close()

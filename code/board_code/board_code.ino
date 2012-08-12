/*

FABMoney 0.3

Author: Massimo Menichinelli
Website:
http://fabmoney.org
http://openp2pdesign.org

License: MIT License

*/

// Pins for the output
int HelloReceiverPin = 12;
int RemoveTagSenderPin = 2;
int HelloSenderPin = 3;
int ErrorPin = 5;
int SuccessPin = 6;
int RemoveTagReceiverPin = 7;

int val = 0;      // variable for reading the pin status
char msg = '  ';   // variable to hold data from serial


#include <SoftwareSerial.h>
SoftwareSerial Rfid(8,11);

void setup()
{
 // Open serial communications and wait for port to open:
  Serial.begin(9600);
  Serial.println("FABMoney: program initiated successfully");

  // Start each software serial port
  Rfid.begin(9600);
 
  // Initializing the pins to be used as output...
  pinMode(HelloReceiverPin, OUTPUT);
  pinMode(HelloSenderPin, OUTPUT);
  pinMode(RemoveTagSenderPin, OUTPUT);
  pinMode(RemoveTagReceiverPin, OUTPUT);
  pinMode(ErrorPin, OUTPUT);
  pinMode(SuccessPin, OUTPUT);
  
  digitalWrite(HelloSenderPin, HIGH);  
}

void loop(){

  // While data is sent over serial assign it to the msg
    while (Serial.available()>0){
        msg=Serial.read();
    }

  // Turn LED on/off if we recieve 'Y'/'N' over serial
  if (msg=='ReadRFID') {       
   
      char tagString[13];
      int index = 0;
      boolean reading = false;
      Rfid.listen();
      // while there is data coming in, read it
      // and send to the hardware serial port:
      while (Rfid.available() > 0) {
        //char inByte = Rfid.read();
        //Serial.write(inByte);
        int readByte = Rfid.read(); //read next available byte
        if(readByte == 2) reading = true; //begining of tag
        if(readByte == 3) reading = false; //end of tag
   
        if(reading && readByte != 2 && readByte != 10 && readByte != 13){
          //store the tag
          tagString[index] = readByte;
          index ++;
        }
      }
    
      Serial.println(tagString); // Send to the serial port the RFID tag read
      clearTag(tagString); //Clear the char of all value
      delay(150); //Reset the RFID reader
   
  } else if (msg=='Error') {
    // Error LED
    digitalWrite(ErrorPin, HIGH); 
    delay(2000);             
    digitalWrite(ErrorPin, LOW);            
  } else if (msg=='Success') {
    // Success LED
    digitalWrite(SuccessPin, HIGH); 
    delay(2000);             
    digitalWrite(SuccessPin, LOW);   
  } else if (msg=='Hello Receiver') {
    // Hello Receiver LED
    digitalWrite(HelloReceiverPin, HIGH); 
    delay(2000);             
    digitalWrite(HelloReceiverPin, LOW);   
  } else if (msg=='Remove Tag Receiver') {
    // Remove Tag Receiver LED
    digitalWrite(RemoveTagReceiverPin, HIGH); 
    delay(2000);             
    digitalWrite(RemoveTagReceiverPin, LOW);   
  } else if (msg=='Hello Sender') {
    // Hello Sender LED         
    digitalWrite(HelloSenderPin, LOW);
  } else if (msg=='Remove Tag Sender') {
    // Remove Tag Sender LED   
    digitalWrite(RemoveTagSenderPin, HIGH); 
    delay(2000);             
    digitalWrite(RemoveTagSenderPin, LOW);       
  }


}


void clearTag(char one[]){
///////////////////////////////////
//clear the char array by filling with null - ASCII 0
//Will think same tag has been read otherwise
///////////////////////////////////
  for(int i = 0; i < strlen(one); i++){
    one[i] = 0;
  }
}

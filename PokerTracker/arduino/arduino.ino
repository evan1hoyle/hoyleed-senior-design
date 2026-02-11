/*
  Knock Sensor

  This sketch reads a piezo element to detect a knocking sound.
  It reads an analog pin and compares the result to a set threshold.
  If the result is greater than the threshold, it writes "knock" to the serial
  port, and toggles the LED on pin 13.

  The circuit:
	- positive connection of the piezo attached to analog in 0
	- negative connection of the piezo attached to ground
	- 1 megohm resistor attached from analog in 0 to ground

  created 25 Mar 2007
  by David Cuartielles <http://www.0j0.org>
  modified 30 Aug 2011
  by Tom Igoe

  This example code is in the public domain.

  https://docs.arduino.cc/built-in-examples/sensors/Knock/
*/


const int knockSensor = A0;  
const int threshold = 800;   
const int knockWindow = 500; 

int knockCount = 0;
unsigned long firstKnockTime = 0;

void setup() {
  Serial.begin(9600);       
}

void loop() {
  int sensorReading = analogRead(knockSensor);

  if (sensorReading >= threshold) {
    unsigned long currentTime = millis();

    

    if (knockCount == 0) {
      knockCount = 1;
      firstKnockTime = currentTime;
      Serial.println("First knock detected...");
      delay(150); 
    } 
    else if (knockCount == 1 && (currentTime - firstKnockTime < knockWindow)) {
      Serial.println("Check! (Double knock detected)");
      knockCount = 0; 
      delay(500);     
    }
  }

  // Reset the count if the user waited too long for the second knock
  if (knockCount == 1 && (millis() - firstKnockTime > knockWindow)) {
    knockCount = 0;
    Serial.println("Timed out - try again.");
  }
}

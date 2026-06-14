// Definir el pin del sensor
const int sensorPin = A0;

void setup() {
  // Inicializar el puerto serie a 9600 baudios
  Serial.begin(9600);
}

void loop() {
  // Leer el valor analógico del sensor
  int sensorValue = analogRead(sensorPin);
  // Convertir el valor a temperatura en grados Celsius
  float temperature = (sensorValue * 0.00488) * 100;
  // Enviar la temperatura a través del puerto serie
  Serial.print(temperature);
  delay(100);
}

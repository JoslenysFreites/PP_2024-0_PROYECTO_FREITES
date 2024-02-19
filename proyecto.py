import numpy as np  # Importa la biblioteca numpy para manipulación de arrays
import matplotlib.pyplot as plt  # Importa la biblioteca matplotlib para graficar
from concurrent.futures import Future, ThreadPoolExecutor  # Importa clases relacionadas con la ejecución concurrente
from threading import Lock, Condition  # Importa clases relacionadas con el manejo de hilos
import os  # Importa el módulo os para interactuar con el sistema operativo
import time  # Importa el módulo time para medir el tiempo de ejecución

class FractalJulia:
    def __init__(self, ancho, alto, max_iteraciones):
        # Inicialización de parámetros
        self.ancho = ancho  # Anchura de la imagen del fractal
        self.alto = alto  # Altura de la imagen del fractal
        self.max_iteraciones = max_iteraciones  # Número máximo de iteraciones para el cálculo del fractal
        self.executor = ThreadPoolExecutor(max_workers=4)  # Executor para ejecución en paralelo con hasta 4 hilos
        self.salida = np.zeros((alto, ancho), dtype=int)  # Matriz de salida del fractal, inicializada con ceros
        self.bloqueo_salida = Lock()  # Bloqueo para sincronizar el acceso a la matriz de salida
        self.condicion = Condition()  # Condición para señalizar cuando los fragmentos se completan
        self.tiempo_comunicacion_total = 0

    def fractal_julia(self, c, z):  
        # Función para calcular el conjunto de Julia
        n = 0
        while abs(z) <= 2 and n < self.max_iteraciones:
            z = z**2 + c
            n += 1
        return n

    def generar_fractal(self, fragmento):
        # Genera un fragmento del conjunto de Julia
        c = complex(self.c_real, self.c_imag)  # C constante compleja para el fractal
        inicio_y, fin_y = fragmento  # Coordenadas y del fragmento a generar
        fragmento_salida = np.zeros((fin_y - inicio_y, self.ancho), dtype=int)  # Matriz para almacenar el fragmento
        for y in range(inicio_y, fin_y):
            imag = y * (3 / self.alto) - 1.5  # Calcula la parte imaginaria de la constante compleja para el punto y
            for x in range(self.ancho):
                real = x * (3 / self.ancho) - 2  # Calcula la parte real de la constante compleja para el punto x
                z = complex(real, imag)  # Crea el número complejo para el punto (x, y)
                fragmento_salida[y - inicio_y, x] = self.fractal_julia(c, z)  # Calcula el valor del fractal en el punto (x, y)
        return fragmento_salida

    def generar_fractal_paralelo(self, c_real, c_imag):
        # Genera el fractal de manera paralela utilizando ThreadPoolExecutor
        self.c_real = c_real  # Asigna el valor real de la constante c
        self.c_imag = c_imag  # Asigna el valor imaginario de la constante c
        start_time = time.time()  # Tiempo de inicio de la generación del fractal

        tamaño_fragmentos = self.alto // 4  # Divide la altura en 4 fragmentos
        fragmentos = [(i * tamaño_fragmentos, (i + 1) * tamaño_fragmentos) for i in range(4)]  # Define los fragmentos a calcular
        fragmentos[-1] = (fragmentos[-1][0], self.alto)  # Ajusta el último fragmento para cubrir el resto de la altura

        futures = []  # Lista para almacenar los objetos Future de las tareas en paralelo
        for fragmento in fragmentos:
            future = self.executor.submit(self.generar_fractal, fragmento)  # Envía la tarea a calcular en paralelo
            future.start_time = time.time()
            future.fragmento = fragmento  # Asocia el fragmento a la tarea para referencia futura
            futures.append(future)  # Agrega el objeto Future a la lista

        # Esperar a que todos los fragmentos se completen
        with self.condicion:
            for future in futures:
                future.add_done_callback(lambda f: self._fragmento_completado(f, f.fragmento))  # Asigna una función de retorno de llamada para cada tarea
            self.condicion.wait()  # Espera hasta que todos los fragmentos estén completos

        tiempo_transcurrido = time.time() - start_time  # Calcula el tiempo transcurrido para generar el fractal
        self.graficar_fractal()  # Grafica el fractal generado
        print(f"Tiempo transcurrido (paralelo): {tiempo_transcurrido:.2f} segundos")  # Imprime el tiempo de ejecución en paralelo

        return tiempo_transcurrido  # Devuelve el tiempo transcurrido en segundos

    def _fragmento_completado(self, future, fragmento):
        # Maneja la finalización de un fragmento y actualiza la matriz de salida
        with self.bloqueo_salida:
            fragmento_salida = future.result()  # Obtiene el resultado del fragmento
            inicio_y, fin_y = fragmento  # Coordenadas del fragmento
            self.salida[inicio_y:fin_y, :] = fragmento_salida  # Actualiza la matriz de salida con el fragmento
            if hasattr(self, 'tiempo_comunicacion_total'):
                self.tiempo_comunicacion_total += time.time() - future.start_time  # Actualiza el tiempo total de comunicación
            else:
                self.tiempo_comunicacion_total = time.time() - future.start_time  # Inicializa el tiempo total de comunicación

        with self.condicion:
            self.condicion.notify()  # Notifica a los hilos que esperan que un fragmento se ha completado

    def generar_fractal_secuencial(self, c_real, c_imag):
        # Genera el fractal de manera secuencial
        self.c_real = c_real  # Asigna el valor real de la constante c
        self.c_imag = c_imag  # Asigna el valor imaginario de la constante c
        tiempo_inicio = time.time()  # Tiempo de inicio de la generación del fractal
        for y in range(self.alto):
            imag = y * (3 / self.alto) - 1.5  # Calcula la parte imaginaria de la constante compleja para el punto y
            for x in range(self.ancho):
                real = x * (3 / self.ancho) - 2  # Calcula la parte real de la constante compleja para el punto x
                z = complex(real, imag)  # Crea el número complejo para el punto (x, y)
                self.salida[y, x] = self.fractal_julia(complex(c_real, c_imag), z)  # Calcula el valor del fractal en el punto (x, y)

        tiempo_transcurrido = time.time() - tiempo_inicio  # Calcula el tiempo transcurrido para generar el fractal
        self.graficar_fractal()  # Grafica el fractal generado
        print(f"Tiempo transcurrido (secuencial): {tiempo_transcurrido:.2f} segundos")  # Imprime el tiempo de ejecución secuencial
        return tiempo_transcurrido  # Devuelve el tiempo transcurrido en segundos

    def graficar_fractal(self, xlim=None, ylim=None, cmap='twilight_shifted'):
        # Grafica el fractal
        plt.imshow(self.salida, cmap=cmap, extent=(-2, 1, -1.5, 1.5))  # Muestra la matriz del fractal como una imagen
        plt.colorbar()  # Muestra la barra de color
        if xlim is not None:
            plt.xlim(xlim)  # Establece los límites en el eje x
        if ylim is not None:
            plt.ylim(ylim)  # Establece los límites en el eje y
        plt.show()  # Muestra la gráfica

def generar_fractal_y_graficar(fractal, c_real, c_imag):
    # Genera el fractal y muestra comparaciones de rendimiento
    tiempo_transcurrido_secuencial = fractal.generar_fractal_secuencial(c_real, c_imag)  # Genera el fractal de manera secuencial
    tiempo_transcurrido_paralelo = fractal.generar_fractal_paralelo(c_real, c_imag)  # Genera el fractal de manera paralela
    
    num_procesadores = os.cpu_count()  # Obtiene el número de procesadores en el sistema
    # Obtener el número de hilos utilizados
    num_hilos = fractal.executor._max_workers

    num_tareas_secuencial = fractal.alto  # Número de tareas en la versión secuencial
    num_tareas_paralelo = len(fractal.salida)  # Número de tareas en la versión paralela
    
    latencia_por_tarea_secuencial = tiempo_transcurrido_secuencial / num_tareas_secuencial  # Calcula la latencia por tarea en la versión secuencial
    latencia_por_tarea_paralelo = tiempo_transcurrido_paralelo / num_tareas_paralelo  # Calcula la latencia por tarea en la versión paralela
    
    throughput_secuencial = num_tareas_secuencial / tiempo_transcurrido_secuencial  # Calcula el throughput en la versión secuencial
    throughput_paralelo = num_tareas_paralelo / tiempo_transcurrido_paralelo  # Calcula el throughput en la versión paralela

    speedup = tiempo_transcurrido_secuencial / tiempo_transcurrido_paralelo  # Calcula el speedup
    eficiencia = speedup / num_procesadores  # Calcula la eficiencia

    tiempo_comunicacion = fractal.tiempo_comunicacion_total
    granularidad = tiempo_transcurrido_paralelo / tiempo_comunicacion
    # Graficar los resultados
    etiquetas = ['Secuencial', 'Paralelo']
    tiempos = [tiempo_transcurrido_secuencial, tiempo_transcurrido_paralelo]
    latencias = [latencia_por_tarea_secuencial, latencia_por_tarea_paralelo]
    throughputs = [throughput_secuencial, throughput_paralelo]

    x = np.arange(len(etiquetas))  # Etiquetas para las barras

    # Gráfico de barras para comparar tiempos de ejecución
    plt.figure(figsize=(10, 5))
    plt.subplot(1, 3, 1)
    plt.bar(x, tiempos)
    plt.xticks(x, etiquetas)
    plt.ylabel('Tiempo (s)')
    plt.title('Comparación de Tiempo de Ejecución')

    # Gráfico de barras para comparar latencias por tarea
    plt.subplot(1, 3, 2)
    plt.bar(x, latencias)
    plt.xticks(x, etiquetas)
    plt.ylabel('Latencia por Tarea (s)')
    plt.title('Comparación de Latencia por Tarea')

    # Gráfico de barras para comparar throughput
    plt.subplot(1, 3, 3)
    plt.bar(x, throughputs)
    plt.xticks(x, etiquetas)
    plt.ylabel('Throughput (tareas/segundo)')
    plt.title('Comparación de Throughput')
    
    plt.tight_layout()
    plt.show()

    print(f"Número de procesadores: {num_procesadores}")
    print(f"Número de hilos utilizados: {num_hilos}")
    print(f"Latencia por tarea (secuencial): {latencia_por_tarea_secuencial:.5f} segundos")
    print(f"Latencia por tarea (paralelo): {latencia_por_tarea_paralelo:.5f} segundos")
    print(f"Throughput (secuencial): {throughput_secuencial:.5f} tareas/segundo")
    print(f"Throughput (paralelo): {throughput_paralelo:.5f} tareas/segundo")
    print(f"Speedup: {speedup:.2f}")
    print(f"Eficiencia: {eficiencia: 2f}")
    print(f"Granularidad: {granularidad:.2f}")  # Imprime la granularidad


def main():
    # Crear una instancia de la clase FractalJulia con dimensiones predeterminadas y 100 iteraciones máximas
    fractal = FractalJulia(800, 800, 100)

    # Permitir al usuario cambiar los valores del fractal y generar fractales
    while True:
        c_real = float(input("Ingrese el valor de c_real (-2 - 2): "))
        c_imag = float(input("Ingrese el valor de c_imag (-2 - 2): "))
        generar_fractal_y_graficar(fractal, c_real, c_imag)  # Genera el fractal y muestra las comparaciones de rendimiento
        continuar = input("¿Desea generar otro fractal? (S/N): ")
        if continuar.lower() != 's':
            break

if __name__ == "__main__":
    main()

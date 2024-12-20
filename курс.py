import datetime
import random
import csv
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkcalendar import DateEntry
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Константы 
SHIFT_START_TIME = datetime.time(6, 0)
SHIFT_END_TIME = datetime.time(3, 0)
PEAK_HOURS_START_1 = datetime.time(7, 0)
PEAK_HOURS_END_1 = datetime.time(9, 0)
PEAK_HOURS_START_2 = datetime.time(17, 0)
PEAK_HOURS_END_2 = datetime.time(19, 0)
SHIFT_CHANGE_TIME_MIN = 10
SHIFT_CHANGE_TIME_MAX = 15
DRIVER_A_WORK_HOURS = 8
DRIVER_A_LUNCH_MINUTES = 60
DRIVER_B_WORK_HOURS = 12
DRIVER_B_BREAK_MINUTES = 15
DRIVER_B_BREAK_FREQUENCY = 120
DRIVER_B_LONG_BREAK_MINUTES = 40
ROUTE_TIME_MIN_MINUTES = 65
ROUTE_TIME_MAX_MINUTES = 75
PASSENGER_FLOW = 1000
PEAK_PASSENGER_PERCENT = 0.7

#  Параметры генетического алгоритма 
POPULATION_SIZE = 50
GENERATIONS = 100
MUTATION_RATE = 0.1

# Дни недели 
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
WEEKEND = ["Saturday", "Sunday"]

#  Структуры данных 
class Driver:
    def __init__(self, driver_type, id):
        self.type = driver_type
        self.schedule = []
        self.total_work_time = datetime.timedelta()
        self.last_break = datetime.datetime.combine(datetime.date.min, SHIFT_START_TIME)
        self.id = id

    def __repr__(self):
        return f"Driver(id={self.id}, type={self.type}, schedule={len(self.schedule)} shifts, worktime = {self.total_work_time})"

class Route:
    def __init__(self, start_time, route_time, driver_id):
        self.start_time = start_time
        self.end_time = start_time + datetime.timedelta(minutes=route_time)
        self.driver_id = driver_id

    def __repr__(self):
        return f"Route(start_time={self.start_time.strftime('%H:%M')}, end_time={self.end_time.strftime('%H:%M')}, driver_id={self.driver_id})"


class Schedule:
    def __init__(self):
        self.routes = []
        self.drivers = []

    def add_route(self, route):
        self.routes.append(route)

    def add_driver(self, driver):
        self.drivers.append(driver)

    def calculate_metrics(self):
        peak_routes = 0
        for route in self.routes:
            if (
                (route.start_time.time() >= PEAK_HOURS_START_1 and route.start_time.time() < PEAK_HOURS_END_1) or
                (route.start_time.time() >= PEAK_HOURS_START_2 and route.start_time.time() < PEAK_HOURS_END_2)
                ):
              peak_routes += 1
        unique_drivers = len(self.drivers)
        total_routes = len(self.routes)
        return total_routes, peak_routes, unique_drivers

# Проверка на час пик 
def is_peak_hour(time):
    return (time >= PEAK_HOURS_START_1 and time < PEAK_HOURS_END_1) or (time >= PEAK_HOURS_START_2 and time < PEAK_HOURS_END_2)

# Проверка выходного дня 
def is_weekend(date):
   return date.strftime('%A') in WEEKEND

# Прямой алгоритм создания расписания 
def create_straight_schedule(num_buses, num_drivers_a, num_drivers_b, current_date):
    schedule = Schedule()
    drivers_a = []
    drivers_b = []
    current_time = datetime.datetime.combine(current_date, SHIFT_START_TIME)

    # Создание водителей типа A
    for i in range(num_drivers_a):
        drivers_a.append(Driver('A', f'A{i+1}'))
    # Создание водителей типа B
    for i in range(num_drivers_b):
       drivers_b.append(Driver('B', f'B{i+1}'))

    available_drivers_a = list(drivers_a)
    available_drivers_b = list(drivers_b)
    
    
    
    while current_time < datetime.datetime.combine(current_date, datetime.time(23, 59)):
        route_time = random.randint(ROUTE_TIME_MIN_MINUTES, ROUTE_TIME_MAX_MINUTES)
        if is_peak_hour(current_time.time()) and not is_weekend(current_date): # Час пик в будни
           
            for _ in range(int(num_buses*PEAK_PASSENGER_PERCENT)):  # 70% маршрутов в часы пик
                if available_drivers_a:
                    driver = available_drivers_a[0]
                    # Проверка, может ли водитель выполнить смену (8 часов)
                    if driver.total_work_time + datetime.timedelta(minutes=route_time) <= datetime.timedelta(hours=DRIVER_A_WORK_HOURS):
                        route = Route(current_time, route_time, driver.id)
                        schedule.add_route(route)
                        driver.schedule.append((route.start_time, route.end_time, 'route'))
                        driver.total_work_time += datetime.timedelta(minutes=route_time)
                    else:
                         available_drivers_a.pop(0)
                         continue
                elif available_drivers_b:
                    driver = available_drivers_b[0]
                    
                    # Проверка, нужно ли дать перерыв
                    if driver.total_work_time >= datetime.timedelta(minutes=DRIVER_B_BREAK_FREQUENCY) and driver.last_break <= current_time - datetime.timedelta(minutes=DRIVER_B_BREAK_FREQUENCY):
                        break_start_time = current_time
                        break_end_time = current_time + datetime.timedelta(minutes=DRIVER_B_LONG_BREAK_MINUTES)
                        driver.schedule.append((break_start_time, break_end_time, 'break'))
                        driver.total_work_time += datetime.timedelta(minutes=DRIVER_B_LONG_BREAK_MINUTES)
                        driver.last_break = break_end_time
                        current_time += datetime.timedelta(minutes=DRIVER_B_LONG_BREAK_MINUTES)
                        continue # Перерыв
                    else:
                        route = Route(current_time, route_time, driver.id)
                        schedule.add_route(route)
                        driver.schedule.append((route.start_time, route.end_time, 'route'))
                        driver.total_work_time += datetime.timedelta(minutes=route_time)
                        
                        
                else:
                    break
        else: # Остальное время (30% в будни и все время в выходные)
            
            passenger_percent = 1 - PEAK_PASSENGER_PERCENT if not is_weekend(current_date) else 1
            for _ in range(int(num_buses * passenger_percent)):
               if available_drivers_a:
                   driver = available_drivers_a[0]
                   
                   # Проверка, может ли водитель выполнить смену (8 часов)
                   if driver.total_work_time + datetime.timedelta(minutes=route_time) <= datetime.timedelta(hours=DRIVER_A_WORK_HOURS):
                        route = Route(current_time, route_time, driver.id)
                        schedule.add_route(route)
                        driver.schedule.append((route.start_time, route.end_time, 'route'))
                        driver.total_work_time += datetime.timedelta(minutes=route_time)
                   else:
                        available_drivers_a.pop(0)
                        continue
               elif available_drivers_b:
                   driver = available_drivers_b[0]
                   
                   # Проверка, нужно ли дать перерыв
                   if driver.total_work_time >= datetime.timedelta(minutes=DRIVER_B_BREAK_FREQUENCY) and driver.last_break <= current_time - datetime.timedelta(minutes=DRIVER_B_BREAK_FREQUENCY):
                        break_start_time = current_time
                        break_end_time = current_time + datetime.timedelta(minutes=DRIVER_B_LONG_BREAK_MINUTES)
                        driver.schedule.append((break_start_time, break_end_time, 'break'))
                        driver.total_work_time += datetime.timedelta(minutes=DRIVER_B_LONG_BREAK_MINUTES)
                        driver.last_break = break_end_time
                        current_time += datetime.timedelta(minutes=DRIVER_B_LONG_BREAK_MINUTES)
                        continue # Перерыв
                   else:
                        route = Route(current_time, route_time, driver.id)
                        schedule.add_route(route)
                        driver.schedule.append((route.start_time, route.end_time, 'route'))
                        driver.total_work_time += datetime.timedelta(minutes=route_time)
               else:
                    break

        current_time += datetime.timedelta(minutes=route_time + random.randint(SHIFT_CHANGE_TIME_MIN, SHIFT_CHANGE_TIME_MAX))

    # Добавляем всех водителей в расписание
    schedule.drivers.extend(drivers_a)
    schedule.drivers.extend(drivers_b)
    return schedule


#  Генерация случайного расписания для генетического алгоритма 
def generate_random_schedule(num_buses, num_drivers_a, num_drivers_b, current_date):
    schedule = Schedule()
    drivers = []
    for i in range(num_drivers_a):
        drivers.append(Driver('A', f'A{i+1}'))
    for i in range(num_drivers_b):
        drivers.append(Driver('B', f'B{i+1}'))
    
    current_time = datetime.datetime.combine(current_date, SHIFT_START_TIME)
    
    while current_time < datetime.datetime.combine(current_date, datetime.time(23, 59)):
        route_time = random.randint(ROUTE_TIME_MIN_MINUTES, ROUTE_TIME_MAX_MINUTES)
        if is_peak_hour(current_time.time()) and not is_weekend(current_date): # Час пик в будни
            for _ in range(int(num_buses * PEAK_PASSENGER_PERCENT)):
                if drivers:
                    driver = random.choice(drivers)
                    if driver.type == 'A' and driver.total_work_time + datetime.timedelta(minutes=route_time) <= datetime.timedelta(hours=DRIVER_A_WORK_HOURS) :
                         route = Route(current_time, route_time, driver.id)
                         schedule.add_route(route)
                         driver.schedule.append((route.start_time, route.end_time, 'route'))
                         driver.total_work_time += datetime.timedelta(minutes=route_time)
                    elif driver.type == 'B':
                        
                        if driver.total_work_time >= datetime.timedelta(minutes=DRIVER_B_BREAK_FREQUENCY) and driver.last_break <= current_time - datetime.timedelta(minutes=DRIVER_B_BREAK_FREQUENCY):
                            break_start_time = current_time
                            break_end_time = current_time + datetime.timedelta(minutes=DRIVER_B_LONG_BREAK_MINUTES)
                            driver.schedule.append((break_start_time, break_end_time, 'break'))
                            driver.total_work_time += datetime.timedelta(minutes=DRIVER_B_LONG_BREAK_MINUTES)
                            driver.last_break = break_end_time
                            current_time += datetime.timedelta(minutes=DRIVER_B_LONG_BREAK_MINUTES)
                            continue
                        else:
                            route = Route(current_time, route_time, driver.id)
                            schedule.add_route(route)
                            driver.schedule.append((route.start_time, route.end_time, 'route'))
                            driver.total_work_time += datetime.timedelta(minutes=route_time)
                    else:
                      drivers.remove(driver)
                      continue
                else:
                    break
        else: # Остальное время (30% в будни и все время в выходные)
            passenger_percent = 1 - PEAK_PASSENGER_PERCENT if not is_weekend(current_date) else 1
            for _ in range(int(num_buses * passenger_percent)):
               if drivers:
                  driver = random.choice(drivers)
                  if driver.type == 'A' and driver.total_work_time + datetime.timedelta(minutes=route_time) <= datetime.timedelta(hours=DRIVER_A_WORK_HOURS) :
                        route = Route(current_time, route_time, driver.id)
                        schedule.add_route(route)
                        driver.schedule.append((route.start_time, route.end_time, 'route'))
                        driver.total_work_time += datetime.timedelta(minutes=route_time)
                  elif driver.type == 'B':
                        if driver.total_work_time >= datetime.timedelta(minutes=DRIVER_B_BREAK_FREQUENCY) and driver.last_break <= current_time - datetime.timedelta(minutes=DRIVER_B_BREAK_FREQUENCY):
                            break_start_time = current_time
                            break_end_time = current_time + datetime.timedelta(minutes=DRIVER_B_LONG_BREAK_MINUTES)
                            driver.schedule.append((break_start_time, break_end_time, 'break'))
                            driver.total_work_time += datetime.timedelta(minutes=DRIVER_B_LONG_BREAK_MINUTES)
                            driver.last_break = break_end_time
                            current_time += datetime.timedelta(minutes=DRIVER_B_LONG_BREAK_MINUTES)
                            continue
                        else:
                            route = Route(current_time, route_time, driver.id)
                            schedule.add_route(route)
                            driver.schedule.append((route.start_time, route.end_time, 'route'))
                            driver.total_work_time += datetime.timedelta(minutes=route_time)
                  else:
                        drivers.remove(driver)
                        continue
               else:
                    break
        current_time += datetime.timedelta(minutes=route_time + random.randint(SHIFT_CHANGE_TIME_MIN, SHIFT_CHANGE_TIME_MAX))

    schedule.drivers.extend(drivers)
    return schedule


#  Функция оценки качества расписания для генетического алгоритма 
def fitness(schedule):
    total_routes, peak_routes, unique_drivers = schedule.calculate_metrics()
    return  total_routes - unique_drivers*0.1


#  Функция скрещивания расписаний для генетического алгоритма 
def crossover(schedule1, schedule2):
    split_point = random.randint(0, min(len(schedule1.routes), len(schedule2.routes)))
    child_schedule = Schedule()
    child_schedule.routes = schedule1.routes[:split_point] + schedule2.routes[split_point:]

    split_point = random.randint(0, min(len(schedule1.drivers), len(schedule2.drivers)))
    child_schedule.drivers = schedule1.drivers[:split_point] + schedule2.drivers[split_point:]
    return child_schedule


#  Функция мутации расписания для генетического алгоритма 
def mutate(schedule):
    if random.random() < MUTATION_RATE:
      if schedule.routes:
        index_route_mutate = random.randint(0, len(schedule.routes)-1)
        new_start_time = schedule.routes[index_route_mutate].start_time + datetime.timedelta(minutes=random.randint(-30,30))
        if new_start_time > datetime.datetime.combine(datetime.date.min, SHIFT_START_TIME) and new_start_time < datetime.datetime.combine(datetime.date.min, SHIFT_END_TIME) + datetime.timedelta(days=1):
            schedule.routes[index_route_mutate] = Route(new_start_time, random.randint(ROUTE_TIME_MIN_MINUTES, ROUTE_TIME_MAX_MINUTES), schedule.routes[index_route_mutate].driver_id)
      if schedule.drivers:
        index_driver_mutate = random.randint(0, len(schedule.drivers) - 1)
        schedule.drivers[index_driver_mutate].type = random.choice(['A', 'B'])
    return schedule


#  Генетический алгоритм 
def genetic_algorithm(num_buses, num_drivers_a, num_drivers_b, current_date):
    population = [generate_random_schedule(num_buses, num_drivers_a, num_drivers_b, current_date) for _ in range(POPULATION_SIZE)]

    for generation in range(GENERATIONS):
        population.sort(key=fitness, reverse=True)
        parents = population[:POPULATION_SIZE // 2]

        offspring = []
        for i in range(0, len(parents), 2):
            if i+1 < len(parents):
                child1 = crossover(parents[i], parents[i+1])
                child2 = crossover(parents[i+1], parents[i])
                offspring.append(mutate(child1))
                offspring.append(mutate(child2))
            else:
                 offspring.append(mutate(parents[i]))

        population = parents + offspring
        population.sort(key=fitness, reverse=True)
        population = population[:POPULATION_SIZE]

    return population[0]

#  Запись расписания в CSV-файл 
def write_schedule_to_csv(straight_schedule, genetic_schedule, filename, current_date):
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Algorithm', 'Driver ID', 'Schedule'])  # Заголовки
        
        for schedule, algorithm_name in [(straight_schedule, "Straight"), (genetic_schedule, "Genetic")]:
          for driver in schedule.drivers:
            shifts_text = ""
            for start, end, type in driver.schedule:
              start_datetime = start
              end_datetime = end
              if type == 'route':
                  shifts_text += f"Маршрут: {start_datetime.strftime('%Y-%m-%d %H:%M')}-{end_datetime.strftime('%Y-%m-%d %H:%M')}, "
              elif type == 'break':
                  shifts_text += f"Перерыв: {start_datetime.strftime('%Y-%m-%d %H:%M')}-{end_datetime.strftime('%Y-%m-%d %H:%M')}, "
            shifts_text = shifts_text.rstrip(", ")
            writer.writerow([algorithm_name, driver.id, shifts_text])

#  Запись сравнения результатов в CSV-файл 
def write_comparison_to_csv(straight_metrics, genetic_metrics, filename):
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Metric', 'Straight Algorithm', 'Genetic Algorithm'])
        writer.writerow(['Total Routes', straight_metrics[0], genetic_metrics[0]])
        writer.writerow(['Peak Routes', straight_metrics[1], genetic_metrics[1]])
        writer.writerow(['Unique Drivers', straight_metrics[2], genetic_metrics[2]])


def display_comparison_window(straight_schedule, genetic_schedule, straight_metrics, genetic_metrics):
    
    comparison_window = tk.Toplevel(root)
    comparison_window.title("Сравнение алгоритмов")
    
    
    labels = ['Total Routes', 'Peak Routes', 'Unique Drivers']
    straight_values = straight_metrics
    genetic_values = genetic_metrics

    fig, axs = plt.subplots(1, 2, figsize=(12, 6))

    bars_straight = axs[0].bar(labels, straight_values, color='skyblue')
    axs[0].set_title('Прямой алгоритм')
    axs[0].set_ylabel('Значение')
    
    for bar, value in zip(bars_straight, straight_values):
         axs[0].text(bar.get_x() + bar.get_width()/2, value,
                    f'{value}',
                    ha='center', va='bottom')
   


    bars_genetic = axs[1].bar(labels, genetic_values, color='lightcoral')
    axs[1].set_title('Генетический алгоритм')
   
    
    for bar, value in zip(bars_genetic, genetic_values):
        axs[1].text(bar.get_x() + bar.get_width()/2, value,
                   f'{value}',
                    ha='center', va='bottom')


    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=comparison_window)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack()

#  Отображение расписания в таблице 
def display_schedule(straight_schedule, genetic_schedule, table, current_date):
    for item in table.get_children():
        table.delete(item)

    schedule_data = []

    for schedule, algorithm_name in [(straight_schedule, "Прямой"), (genetic_schedule, "Генетический")]:
        for driver in schedule.drivers:
            driver_schedules = []
            for start, end, type in driver.schedule:
                driver_schedules.append((start, end, type))

            shifts_text = ""
            total_work_time = 0
            total_break_time = 0

            for start, end, type in driver_schedules:
                if type == 'route':
                    total_work_time += (end - start).total_seconds() / 60
                    shifts_text += f"Маршрут: {start.strftime('%H:%M')}-{end.strftime('%H:%M')}, "
                elif type == 'break':
                    total_break_time += (end - start).total_seconds() / 60
                    shifts_text += f"Перерыв: {start.strftime('%H:%M')}-{end.strftime('%H:%M')}, "

            shifts_text = shifts_text.rstrip(", ")

            schedule_data.append((algorithm_name, driver.id, shifts_text, f"{int(total_work_time)} мин", f"{int(total_break_time)} мин"))

    table.heading("Algorithm", text="Алгоритм")
    table.heading("Driver ID", text="Водитель")
    table.heading("Schedule", text="Расписание")
    table.heading("Work Time", text="Время работы")
    table.heading("Break Time", text="Время перерыва")
    
    tag_counter = 0
    for algorithm, driver_id, shifts, work_time, break_time in schedule_data:
        tag = f"tag{tag_counter}"
        if algorithm == "Прямой":
            table.insert("", "end", values=[algorithm, driver_id, shifts, work_time, break_time], tags=(tag,))
            table.tag_configure(tag, background="#e0f7fa")
        else:
            table.insert("", "end", values=[algorithm, driver_id, shifts, work_time, break_time], tags=(tag,))
            table.tag_configure(tag, background="#ffebee")
        tag_counter += 1
    
    table.column("Algorithm", width=100, anchor='center')
    table.column("Driver ID", width=80, anchor='center')
    table.column("Schedule", width=400, anchor='w')
    table.column("Work Time", width=100, anchor='center')
    table.column("Break Time", width=100, anchor='center')

    for item in table.get_children():
       if table.index(item) % 2 != 0 :
         table.item(item,  tags=('oddrow',))
    table.tag_configure('oddrow', background='#f0f0f0')

#  Функция запуска алгоритмов и отображения результатов 
def run_algorithms_and_display():
    try:
        num_buses = int(buses_entry.get())
        num_drivers_a = int(drivers_a_entry.get())
        num_drivers_b = int(drivers_b_entry.get())
        selected_date = date_entry.get_date()
    
        straight_schedule = create_straight_schedule(num_buses, num_drivers_a, num_drivers_b, selected_date)
        genetic_schedule = genetic_algorithm(num_buses, num_drivers_a, num_drivers_b, selected_date)

        straight_metrics = straight_schedule.calculate_metrics()
        genetic_metrics = genetic_schedule.calculate_metrics()

        display_schedule(straight_schedule, genetic_schedule, schedule_table, selected_date)

        metrics_text.config(text=f"Прямой: Маршрутов={straight_metrics[0]}, Маршрутов в пик={straight_metrics[1]}, Водителей={straight_metrics[2]} "
                                 f"Генетический: Маршрутов={genetic_metrics[0]}, Маршрутов в пик={genetic_metrics[1]}, Водителей={genetic_metrics[2]}")
        write_comparison_to_csv(straight_metrics, genetic_metrics, 'comparison_results.csv')
        display_comparison_window(straight_schedule, genetic_schedule, straight_metrics, genetic_metrics)

    except ValueError as e:
        metrics_text.config(text=f"Ошибка: {e}")


#  Функция сохранения расписания в файл 
def save_schedule_to_file():
   filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV файлы", "*.csv")])
   if filename:
        num_buses = int(buses_entry.get())
        num_drivers_a = int(drivers_a_entry.get())
        num_drivers_b = int(drivers_b_entry.get())
        selected_date = date_entry.get_date()
        straight_schedule = create_straight_schedule(num_buses, num_drivers_a, num_drivers_b, selected_date)
        genetic_schedule = genetic_algorithm(num_buses, num_drivers_a, num_drivers_b, selected_date)
        write_schedule_to_csv(straight_schedule, genetic_schedule, filename, selected_date)

        print("Расписание сохранено в:", filename)


#  Создание основного окна 
root = tk.Tk()
root.title("Генератор расписания автобусов")

#  Поля ввода 
# Ввод количества автобусов
buses_label = tk.Label(root, text="Количество автобусов:")
buses_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
buses_entry = tk.Entry(root)
buses_entry.insert(0, "8")
buses_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

# Ввод количества водителей типа A
drivers_a_label = tk.Label(root, text="Количество водителей (Тип A):")
drivers_a_label.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
drivers_a_entry = tk.Entry(root)
drivers_a_entry.insert(0, "10")
drivers_a_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

# Ввод количества водителей типа B
drivers_b_label = tk.Label(root, text="Количество водителей (Тип B):")
drivers_b_label.grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
drivers_b_entry = tk.Entry(root)
drivers_b_entry.insert(0, "5")
drivers_b_entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

# Поле для выбора даты
date_label = tk.Label(root, text="Выберите дату:")
date_label.grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
date_entry = DateEntry(root, width=12, background='white',
                           year=datetime.date.today().year,
                            month=datetime.date.today().month,
                            day=datetime.date.today().day
                           )
date_entry.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)

#  Кнопка запуска алгоритмов 
run_button = tk.Button(root, text="Сгенерировать расписание", command=run_algorithms_and_display)
run_button.grid(row=4, column=0, columnspan=2, padx=5, pady=10)

#  Таблица для отображения расписания 
schedule_table = ttk.Treeview(root, columns=("Algorithm", "Driver ID", "Schedule", "Work Time", "Break Time"), show="headings")
schedule_table.grid(row=5, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")

root.grid_rowconfigure(5, weight=1)
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)

#Текст для вывода метрик 
metrics_text = tk.Label(root, text="")
metrics_text.grid(row=6, column=0, columnspan=2, padx=5, pady=5)

# Кнопка сохранения расписания
save_button = tk.Button(root, text="Сохранить расписание", command=save_schedule_to_file)
save_button.grid(row=7, column=0, columnspan=2, padx=5, pady=10)

root.mainloop()

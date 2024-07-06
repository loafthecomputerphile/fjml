import matplotlib.pyplot as plt
import timeit

# Initialize a list with 1M numbers
numbers = [i for i in range(0, 1000000)]

# Create a new list by squaring the numbers with for loop
def for_loop():
    for num in numbers:
        yield (num ** 2) ** 2

# Create a new list by squaring the numbers with set comprehension
def comprehension():
    return ((num ** 2) ** 2 for num in numbers)

# Compute the runtime of a function
def measure_runtime(func, n_times):
    total_runtime = 0.0
    for i in range(n_times):
        start = timeit.default_timer()

        func()

        stop = timeit.default_timer()
        total_runtime += stop - start
    return total_runtime / n_times


n_runs = 10

# Compute runtimes for both for loop and list comprehension approaches
loop_average = measure_runtime(for_loop, n_runs)
comprehension_average = measure_runtime(comprehension, n_runs)

print(
    f"For loop yileds average runtime {loop_average} with {n_runs} iterations")
print(
    f"Comprehension yileds average runtime {comprehension_average} with {n_runs} iterations")


fig, ax = plt.subplots()
approaches = ['For loop', 'Comprehension']
runtimes = [loop_average, comprehension_average]
rects = ax.bar(approaches, runtimes)

for rect, label in zip(rects, runtimes):
    height = rect.get_height()
    ax.text(rect.get_x() + rect.get_width() / 2,
            height, label, ha='center', va='bottom')

plt.show()
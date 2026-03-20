"""Demo script to test the Python Inspector."""
import inspector


def greet(name):
    message = f"Hello, {name}!"
    return message


def fibonacci(n):
    a, b = 0, 1
    result = []
    for i in range(n):
        result.append(a)
        a, b = b, a + b
    return result


# --- This part runs WITHOUT the inspector ---
print("=== Before inspector ===")
name = "World"
greeting = greet(name)
print(greeting)

# --- Start inspecting from here ---
inspector.start()

numbers = [1, 2, 3, 4, 5]
total = sum(numbers)
average = total / len(numbers)

fib = fibonacci(6)

inspector.stop()
# --- Inspector is off again ---

print(f"\n=== After inspector ===")
print(f"Fibonacci: {fib}")
print(f"Average of {numbers} = {average}")

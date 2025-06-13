import array

# Base class with Exception Handling and OOP
class DataProcessor:
    def __init__(self, name):
        self.name = name
        self.int_array = array.array('i', [5, 2, 9, 1, 5, 6])  # array
        self.int_list = list(self.int_array)  # convert to list

    def display_data(self):
        print(f"Original array: {self.int_array.tolist()}")
        print(f"List version: {self.int_list}")

    def divide(self, a, b):
        try:
            return a / b
        except ZeroDivisionError:
            print("Attempted division by zero.")
            return None

    def factorial(self, n):  # Recursion
        if n <= 1:
            return 1
        return n * self.factorial(n - 1)

    def sort_data(self):  # Bubble Sort
        data = self.int_list[:]
        n = len(data)
        for i in range(n):
            for j in range(0, n - i - 1):
                if data[j] > data[j + 1]:
                    data[j], data[j + 1] = data[j + 1], data[j]
        return data

# Inherited class
class AdvancedProcessor(DataProcessor):
    def __init__(self, name):
        super().__init__(name)

    def process_all(self):
        print(f"Processing data for: {self.name}")
        self.display_data()

        print("Sorted data:", self.sort_data())
        print("Division 10/2:", self.divide(10, 2))
        print("Division 10/0 (should handle exception):", self.divide(10, 0))
        print("Factorial of 5:", self.factorial(5))

if __name__ == "__main__":
    processor = AdvancedProcessor("SecurityTool")
    processor.process_all()

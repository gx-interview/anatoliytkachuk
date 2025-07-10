# Step 1
Clone the repository

# Step 2
Create a new branch, use your name as the branch name

# Step 3
Create a python file to implement following functionality
 - Load csv data from source.csv file
 - Convert values in datetime column from timezone UTC to UTC+6
 - Add new column - total - where:
    - Product A is an outright and, if product purity is 'Pure', the total should therefore be calculated as amount * price
    - Product B is a diff and the total should be found by taking its respective Product A price (the one with matching timestamp) from the price of Product B given, before multiplying by the amount of Product B
    - If the Product purity is 'Impure' prices should be reduced to 3/4 of its given value when calculating the total 
 - Save the result to the new file result.csv

# Step 4
Commit and push the python file and generated result.csv to the branch

# Step 5
Create a Pull Request to main branch


# Solution documentation 


This script provides an efficient price calculating mechanism from a `source.csv` file and exporting the results to `result.csv`. It is designed for high performance, code quality, and extensibility.

It was made to ensure:

- SOLID Architecture : The code is separated into two classes, each with a single responsibility: `DataHandler` for data I/O and `PriceCalculator` for all business logic and calculations(in the future these classes should be moved to different modules instead of keeping them in a single module).

- High-Performance Calculations: Uses vectorized NumPy and pandas operations (`np.select`) for fast and memory-efficient processing, avoiding slow row-by-row iteration.

- Extensible Design: Built to support new data sources (that potentially can appear)like databases or APIs in the future with minimal code changes.

- Comprehensive Unit Tests: Includes a test file built with `unittest` to ensure that the script functions correctly


Requirements:
- Python 3.8+
- Pandas, NumPy


How to execute:

1. Clone the repo:

```git clone https://github.com/gx-interview/anatoliytkachuk.git```

```cd <your-repo-directory>```

2. Install requirements:

```pip install -r requirements.txt```

3. Run the script:

```python price_calculation.py ```

4. Run the tests:

 ```python -m unittest test_price_calculation.py```

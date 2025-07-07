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

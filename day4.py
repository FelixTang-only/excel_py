# 自动填充单元格 类似Excel中拖动下拉自动填充功能

import pandas as pd

books = pd.read_excel('/Users/apple/Work/excel_py/day4.xlsx', skiprows=9, usecols='F:J', dtype={'name': str})

# print(books)

for i in books.index:
    # print(books['id'].at[i])
    books['id'].at[i] = i + 1
    # books['name'].at[i] = 'kim' + str(int(books['name'].at[i].split('kim')[1]) + i)
    # print(books['name'].at[i].split('kim'))
    if i == 0:
        books['name'].at[i] = 'kim' + str(int(books['name'].at[i].split('kim')[1]) + i)
    else:
        books['name'].at[i] = 'kim' + str(int(books['name'].at[i - 1].split('kim')[1]) + i)

print(books)
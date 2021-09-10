# 自动填充单元格 类似Excel中拖动下拉自动填充功能

import pandas as pd
from datetime import date,timedelta

books = pd.read_excel('/Users/apple/Work/excel_py/day4.xlsx', skiprows=9, usecols='F:J', dtype={'name': str})

# print(books)
start = date(2022, 1, 1)
def cp_month(d, i):
    yd = i // 12
    m = d.month + i % 12
    if m != 12:
        yd += m // 12
        m = m % 12
    return date(d.year + yd, m, d.day)

for i in books.index:
    # print(books['id'].at[i])
    books['id'].at[i] = i + 1
    # books['name'].at[i] = 'kim' + str(int(books['name'].at[i].split('kim')[1]) + i)
    # print(books['name'].at[i].split('kim'))
    if i == 0:
        books['name'].at[i] = 'kim' + str(int(books['name'].at[i].split('kim')[1]) + i)
    else:
        books['name'].at[i] = 'kim' + str(int(books['name'].at[i - 1].split('kim')[1]) + i)
    # 累加年份
    # books['date'].at[i] = date(start.year + i, start.month, start.day)
    # 累加日
    # books['date'].at[i] = start + timedelta(days=i) 
    # 累加月份
    books['date'].at[i] = cp_month(start, i)

a = books.set_index('id')
a.to_excel('/Users/apple/Work/excel_py/day5.xlsx')

# print(books)
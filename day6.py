# 函数填充，计算列
import pandas as pd

table = pd.read_excel('/Users/apple/Work/excel_py/day6.xlsx', index_col='id')

# table['总价'] = table['单价'] * table['库存']

# for i in table.index:
#     table['总价'].at[i] = table['单价'].at[i] * table['库存'].at[i]

# for i in range(3, 8):
#     table['总价'].at[i] = table['单价'].at[i] * table['库存'].at[i]

# table['单价'] = table['单价'] + 1

# def add_1(x):
#     return x + 1
# table['单价'] = table['单价'].apply(add_1)

table['单价'] = table['单价'].apply(lambda x: x + 1)


print(table)

# x = lambda a: a + 1
# x(1)
# print(x(1))

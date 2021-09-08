# // 行 列 单元格
from os import name
import pandas as pd

# d = {'x': 100, 'y': 200, 'z': 300}
# s1 = pd.Series(d)
# # print(s1)
# print(s1.index)

# l1 = [100, 200, 300]
# l2 = ['x', 'y', 'z']
# s1 = pd.Series(l1, index=l2)
# print(s1)

s1 = pd.Series([1, 2, 3], index=[1, 2, 3], name='a')
# print(s1)
s2 = pd.Series([10, 20, 30], index=[1, 2, 3], name='b')
s3 = pd.Series([100, 200, 300], index=[1, 2, 3], name='c')

df = pd.DataFrame({s1.name: s1, s2.name: s2, s3.name: s3 })
print(df)

a = df.set_index('a')
a.to_excel('/Users/apple/Work/excel_py/day3-output.xlsx')

import pandas as pd

def reorder_csv_columns():
    # 读取CSV文件
    df = pd.read_csv('resources/stopovers.csv')
    
    # 重新排序列
    new_columns = ['start_date', 'train_number', 'station_name', 
                  'arrival_time', 'departure_time', 'stop_order']
    df = df[new_columns]
    
    # 保存回CSV文件
    df.to_csv('resources/stopovers.csv', index=False)

if __name__ == '__main__':
    reorder_csv_columns()
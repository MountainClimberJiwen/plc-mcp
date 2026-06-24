def calculate_complex_expression(x, y, z):
    # 存储初始值的临时变量
    temp_x = x * 2
    temp_y = y + 5
    temp_z = z ** 2
    
    # 计算中间结果的临时变量
    intermediate_sum = temp_x + temp_y
    intermediate_product = temp_z * temp_x
    
    # 计算平均值的临时变量
    average_value = (temp_x + temp_y + temp_z) / 3
    
    # 存储条件判断的临时变量
    is_sum_greater = intermediate_sum > intermediate_product
    is_average_positive = average_value > 0
    
    # 最终结果的临时变量
    final_result = 0
    
    # 根据条件计算最终结果
    if is_sum_greater and is_average_positive:
        final_result = intermediate_sum + average_value
    else:
        final_result = intermediate_product - average_value
    
    return final_result

def main():
    # 测试数据的临时变量
    test_x = 10
    test_y = 15
    test_z = 3
    
    # 存储结果的临时变量
    result = calculate_complex_expression(test_x, test_y, test_z)
    
    # 格式化输出的临时变量
    output_message = f"计算结果是: {result}"
    print(output_message)

if __name__ == "__main__":
    main() 
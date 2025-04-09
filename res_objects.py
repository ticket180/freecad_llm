
import importlib
import ast

def parse_input(input_str):
    """
    解析输入字符串，提取变量名、方法路径、参数和右侧值。
    """
    tree = ast.parse(input_str)
    # 将 AST 转换为字符串

    output_name = None
    method_path = None
    converted_args = []
    right_value = None

    for node in ast.walk(tree):
        # 检查是否是赋值语句
        if isinstance(node, ast.Assign):
            # 提取目标变量名或属性路径
            if isinstance(node.targets[0], ast.Name):  # 普通变量名
                output_name = node.targets[0].id
            elif isinstance(node.targets[0], ast.Attribute):  # 属性赋值
                output_name = extract_attribute_path(node.targets[0])
            else:
                raise TypeError(f"Unsupported target type: {type(node.targets[0])}")

            # 提取右侧值
            right_value = extract_right_value(node.value)

            # 如果右侧是函数调用，提取方法路径和参数
            if isinstance(node.value, ast.Call):
                method_path, converted_args = extract_method_and_args(node.value)

        # 检查是否是直接的函数调用
        elif isinstance(node, ast.Call):
            method_path, converted_args = extract_method_and_args(node)

    return output_name, method_path, converted_args, right_value


def extract_method_and_args(call_node):
    """
    从函数调用节点中提取方法路径和参数。
    """
    # 提取方法路径
    if isinstance(call_node.func, ast.Attribute):  # 方法调用
        method_path = extract_attribute_path(call_node.func)
    elif isinstance(call_node.func, ast.Name):  # 普通函数调用
        method_path = call_node.func.id
    else:
        raise TypeError(f"Unsupported function type: {type(call_node.func)}")

    # 提取参数值
    converted_args = []
    for arg in call_node.args:
        if isinstance(arg, ast.Str):  # 字符串字面量
            converted_args.append(arg.s)
        elif isinstance(arg, ast.Num):  # 数字字面量
            converted_args.append(arg.n)
        elif isinstance(arg, ast.UnaryOp):  # 一元操作符（如负号）
            if isinstance(arg.op, ast.USub):  # 负号
                operand = arg.operand
                if isinstance(operand, ast.Num):
                    converted_args.append(-operand.n)
                else:
                    raise TypeError(f"Unsupported UnaryOp operand: {type(operand)}")
            else:
                raise TypeError(f"Unsupported UnaryOp operator: {type(arg.op)}")
        elif isinstance(arg, ast.Name):  # 变量名
            converted_args.append(arg.id)
        else:
            raise TypeError(f"Unsupported argument type: {type(arg)}")

    return method_path, converted_args


def extract_attribute_path(attribute_node):
    """
    递归提取嵌套属性路径。
    """
    parts = []
    current_node = attribute_node
    while isinstance(current_node, ast.Attribute):
        parts.append(current_node.attr)
        current_node = current_node.value
    if isinstance(current_node, ast.Name):
        parts.append(current_node.id)
    else:
        raise TypeError(f"Unsupported node type in attribute path: {type(current_node)}")
    return ".".join(reversed(parts))


def extract_right_value(value_node):
    """
    提取右侧值。
    """
    if isinstance(value_node, ast.Call):
        return None  # 如果右侧是函数调用，则返回 None
    elif isinstance(value_node, ast.Str):
        return value_node.s
    elif isinstance(value_node, ast.Num):
        return value_node.n
    elif isinstance(value_node, ast.UnaryOp):  # 处理一元操作符
        if isinstance(value_node.op, ast.USub):  # 负号
            operand = value_node.operand
            if isinstance(operand, ast.Num):
                return -operand.n
            else:
                raise TypeError(f"Unsupported UnaryOp operand: {type(operand)}")
        else:
            raise TypeError(f"Unsupported UnaryOp operator: {type(value_node.op)}")
    else:
        raise TypeError(f"Unsupported value type: {type(value_node)}")



class Res_Object:
        def __init__(self, name, obj):
            self.name = name
            self.obj = obj
class Res_Objects:
    def __init__(self):
        self.objects= []

   
    def add_object(self, name,obj):
        res_object= Res_Object(name,obj)    
        self.objects.append(res_object)
        print("add_to_list:",name,type(obj),obj)
        
    def objects_information(self):
        
        return str([(obj.name,type(obj.obj).__name__) for obj in self.objects])
    def get_object(self, name):
        for obj in self.objects:
            if obj.name == name:
                return obj.obj
        return None
   

        

    def handle_function(self,rpc_request_queue,rpc_response_queue,commands):
        #print(" 解析结果检查：",commands)
        input_strs=[item.strip() for item in commands.split("\n") if item.strip()]
        for input_str in input_strs:
            output_name, method_name, args,right_value=parse_input(input_str)
           
            if  method_name:
                parts = method_name.split('.')
                method = self.get_object(parts[0])
                if not method:    method = importlib.import_module(parts[0])
                
                for part in parts[1:]:method = getattr(method, part, None)
                formatted_args = [f'"{arg}"' if isinstance(arg, str) else str(arg) for arg in args]
                print(f"调用函数：{method_name}({', '.join(formatted_args)})")
                rpc_request_queue.put(lambda: method(*args))
             
                res = rpc_response_queue.get() 
            
                if output_name:
                    if not self.get_object(output_name):self.add_object(output_name,res)
                    else:self.get_object(output_name).obj=res
            else:
                parts = output_name.split('.')
                obj = self.get_object(parts[0])  # 获取顶层对象（如 cube）
                for part in parts[1:-1]:  # 遍历中间层级的属性
                    obj = getattr(obj, part, None)

                # 设置最后一层属性
                if len(parts) > 1:
                    attr_name = parts[-1]  # 属性名（如 "Height"）
                    setattr(obj, attr_name, right_value)  # 使用 setattr 设置属性值

                print("设置属性：", output_name, getattr(obj, attr_name))
        return self.objects_information()        
if __name__ == "__main__":
    command = "doc.recompute()"
    output_name, method_path, converted_args, right_value = parse_input(command)
    tree = ast.parse(command)
    # 将 AST 转换为字符串
    ast_str = ast.dump(tree, indent=4)

    # 保存到本地文件
    with open("ast_output.txt", "w", encoding="utf-8") as f:
        f.write(ast_str)
    print(f"Output Name: {output_name}")
    print(f"Method Path: {method_path}")
    print(f"Converted Args: {converted_args}")
    print(f"Right Value: {right_value}")
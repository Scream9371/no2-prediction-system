"""
城市配置模块
动态管理大湾区城市ID和名称的映射关系
"""
import os
import json
import tempfile

# 大湾区城市名称列表
GREATER_BAY_AREA_CITIES = [
    "广州",
    "深圳", 
    "珠海",
    "佛山",
    "惠州",
    "东莞",
    "中山",
    "江门",
    "肇庆",
    "香港特别行政区",
    "澳门特别行政区"
]

# 运行时城市映射缓存
_city_id_cache = {}
_name_to_id_cache = {}

# 缓存文件路径
_CACHE_FILE = os.path.join(tempfile.gettempdir(), 'no2_city_mappings.json')


def _load_cache_from_file():
    """从文件加载缓存"""
    global _city_id_cache, _name_to_id_cache
    
    if os.path.exists(_CACHE_FILE):
        try:
            with open(_CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                _city_id_cache = data.get('city_id_cache', {})
                _name_to_id_cache = data.get('name_to_id_cache', {})
                return True
        except Exception as e:
            print(f"加载城市映射缓存失败: {e}")
    return False


def _save_cache_to_file():
    """保存缓存到文件"""
    try:
        data = {
            'city_id_cache': _city_id_cache,
            'name_to_id_cache': _name_to_id_cache
        }
        with open(_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存城市映射缓存失败: {e}")


def init_city_mappings():
    """
    初始化城市ID映射，通过API动态获取城市ID
    应在应用启动时调用
    
    Returns:
        bool: 初始化是否成功
    """
    global _city_id_cache, _name_to_id_cache
    
    # 先尝试从文件加载缓存
    if _load_cache_from_file() and _city_id_cache and _name_to_id_cache:
        print(f"从缓存加载城市映射 ({len(_city_id_cache)} 个城市)")
        return True
    
    # 检查内存中是否已经初始化过
    if _city_id_cache and _name_to_id_cache:
        print(f"城市映射已在内存中初始化 ({len(_city_id_cache)} 个城市)")
        return True
    
    print("正在初始化城市映射...")
    try:
        from api.heweather.client import HeWeatherClient
        client = HeWeatherClient()
        
        for city_name in GREATER_BAY_AREA_CITIES:
            city_id = client.get_city_id(city_name)
            if city_id:
                _city_id_cache[city_id] = city_name
                _name_to_id_cache[city_name] = city_id
            else:
                print(f"警告: 无法获取城市 {city_name} 的ID")
                return False
                
        print(f"成功初始化 {len(_city_id_cache)} 个城市的映射关系")
        
        # 保存缓存到文件
        _save_cache_to_file()
        
        return True
        
    except Exception as e:
        print(f"初始化城市映射失败: {e}")
        return False


def get_city_name(city_id: str) -> str:
    """
    根据城市ID获取城市名称
    
    Args:
        city_id (str): 城市ID
        
    Returns:
        str: 城市名称，如果ID无效返回None
    """
    return _city_id_cache.get(city_id)


def get_city_id(city_name: str) -> str:
    """
    根据城市名称获取城市ID
    
    Args:
        city_name (str): 城市名称
        
    Returns:
        str: 城市ID，如果名称无效返回None
    """
    return _name_to_id_cache.get(city_name)


def get_all_cities() -> list:
    """
    获取所有支持的城市列表
    
    Returns:
        list: 包含城市ID和名称的字典列表
    """
    return [{"id": city_id, "name": name} for city_id, name in _city_id_cache.items()]


def is_supported_city(city_id: str) -> bool:
    """
    检查城市ID是否被支持
    
    Args:
        city_id (str): 城市ID
        
    Returns:
        bool: 是否支持该城市
    """
    return city_id in _city_id_cache
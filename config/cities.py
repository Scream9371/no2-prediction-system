"""
城市配置模块
动态管理大湾区城市ID和名称的映射关系
"""

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


def init_city_mappings():
    """
    初始化城市ID映射，通过API动态获取城市ID
    应在应用启动时调用
    
    Returns:
        bool: 初始化是否成功
    """
    global _city_id_cache, _name_to_id_cache
    
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


def refresh_city_mappings() -> bool:
    """
    刷新城市ID映射（重新从API获取）
    
    Returns:
        bool: 刷新是否成功
    """
    global _city_id_cache, _name_to_id_cache
    _city_id_cache.clear()
    _name_to_id_cache.clear()
    return init_city_mappings()


def get_supported_city_names() -> list:
    """
    获取支持的城市名称列表
    
    Returns:
        list: 城市名称列表
    """
    return GREATER_BAY_AREA_CITIES.copy()
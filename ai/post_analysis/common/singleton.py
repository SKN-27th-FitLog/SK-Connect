"""클래스별 인스턴스를 하나만 두는 메타클래스."""


class Singleton(type):
    """동일 클래스에 대해 최초 생성분만 재사용한다."""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        """인스턴스가 없을 때만 실제 생성자를 호출한다."""
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

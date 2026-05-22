"""PA-L0-SNG: common.singleton (Level 0)."""

from common.singleton import Singleton


def test_pa_l0_sng_001_same_class_same_instance() -> None:
    """PA-L0-SNG-001 [불변]: 동일 클래스는 Singleton 인스턴스 하나."""
    class A(metaclass=Singleton):
        def __init__(self) -> None:
            self.value = 1

    assert A() is A()


def test_pa_l0_sng_002_different_classes_different_instances() -> None:
    """PA-L0-SNG-002 [경계]: 서로 다른 Singleton 클래스는 인스턴스 분리."""
    class A(metaclass=Singleton):
        pass

    class B(metaclass=Singleton):
        pass

    assert A() is not B()

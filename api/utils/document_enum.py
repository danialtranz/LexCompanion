from enum import Enum

class DocumentType(Enum):
    LAW = "luat"
    DECREE = "nghi_dinh"
    CIRCULAR = "thong_tu"
    LAW_AMENDING = "luat_sua_doi"
    DECREE_AMENDING = "nghi_dinh_sua_doi"
    CIRCULAR_AMENDING = "thong_tu_sua_doi"



class LegalHierarchyLevel(Enum):
  CHAPTER = "chuong",
  ARTICLE = "dieu",
  CLAUSE = "khoan",
  POINT = "diem"

class GovernmentBodyType(Enum):
  NATIONAL_ASSEMBLY = "quoc_hoi",
  GOVERNMENT = "chinh_phu",
  MINISTRY = "bo_truong",
  DEPUTY_MINISTER = "thu_truong"


class SignerRoleType(Enum):
  CHAIRMAN_NATIONAL_ASSEMBLY = "chu_tich_quoc_hoi",
  PRIME_MINISTER = "thu_tuong",
  MINISTER = "bo_truong",
  DEPUTY_MINISTER = "thu_truong",

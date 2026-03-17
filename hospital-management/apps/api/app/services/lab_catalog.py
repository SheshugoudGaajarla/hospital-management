from dataclasses import dataclass


@dataclass(frozen=True)
class LabCatalogItem:
    code: str
    name: str
    department: str
    category: str


LAB_TEST_CATALOG: tuple[LabCatalogItem, ...] = (
    LabCatalogItem(code="CBC", name="Complete Blood Count", department="common", category="Hematology"),
    LabCatalogItem(code="HB", name="Hemoglobin", department="common", category="Hematology"),
    LabCatalogItem(code="ESR", name="ESR", department="pediatrics", category="Inflammation"),
    LabCatalogItem(code="CRP", name="CRP", department="pediatrics", category="Inflammation"),
    LabCatalogItem(code="URINE_ROUTINE", name="Urine Routine", department="common", category="Routine"),
    LabCatalogItem(code="STOOL_ROUTINE", name="Stool Routine", department="pediatrics", category="Routine"),
    LabCatalogItem(code="DENGUE", name="Dengue Test", department="pediatrics", category="Fever Panel"),
    LabCatalogItem(code="MALARIA", name="Malaria Test", department="pediatrics", category="Fever Panel"),
    LabCatalogItem(code="WIDAL", name="Widal Test", department="pediatrics", category="Fever Panel"),
    LabCatalogItem(code="BLOOD_SUGAR", name="Blood Sugar", department="common", category="Biochemistry"),
    LabCatalogItem(code="THYROID_PROFILE", name="Thyroid Profile", department="common", category="Hormones"),
    LabCatalogItem(code="VITAMIN_D", name="Vitamin D", department="pediatrics", category="Nutrition"),
    LabCatalogItem(code="CALCIUM", name="Calcium", department="pediatrics", category="Nutrition"),
    LabCatalogItem(code="BLOOD_GROUP", name="Blood Group", department="gynecology", category="Pre-Procedure"),
    LabCatalogItem(code="UPT", name="Urine Pregnancy Test", department="gynecology", category="Pregnancy"),
    LabCatalogItem(code="BETA_HCG", name="Beta HCG", department="gynecology", category="Pregnancy"),
    LabCatalogItem(code="PAP_SMEAR", name="Pap Smear", department="gynecology", category="Screening"),
    LabCatalogItem(code="HORMONE_PROFILE", name="Hormone Profile", department="gynecology", category="Hormones"),
    LabCatalogItem(code="CULTURE", name="Culture and Sensitivity", department="gynecology", category="Microbiology"),
    LabCatalogItem(code="LFT", name="Liver Function Test", department="common", category="Biochemistry"),
    LabCatalogItem(code="KFT", name="Kidney Function Test", department="common", category="Biochemistry"),
    LabCatalogItem(code="LIPID_PROFILE", name="Lipid Profile", department="common", category="Biochemistry"),
    LabCatalogItem(code="HBA1C", name="HbA1c", department="common", category="Diabetes"),
)

LAB_TEST_LOOKUP = {item.code: item for item in LAB_TEST_CATALOG}
LAB_TEST_NAME_LOOKUP = {item.name.lower(): item for item in LAB_TEST_CATALOG}


def get_lab_catalog_item(code: str) -> LabCatalogItem | None:
    return LAB_TEST_LOOKUP.get(code.strip().upper())


def match_lab_catalog_by_name(name: str) -> LabCatalogItem | None:
    return LAB_TEST_NAME_LOOKUP.get(name.strip().lower())

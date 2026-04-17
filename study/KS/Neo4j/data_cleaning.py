# 로그 
import logging
logger = logging.getLogger(__name__)

# 패키지
import pandas as pd





if __name__ == '__main__':
    
    logging.basicConfig(level=logging.INFO)

    ############################################################
    # 데이터 파일 로드 
    ############################################################
    df = pd.read_csv('Neo4j\\data\\ItemGroup_Equipment.csv')
    logger.info('=== 로드된 데이터 확인 ===')
    logger.info(df.columns.tolist())
    logger.info(df.shape)


    ############################################################
    # 컬럼 드랍 (나중에는 특정 컬럼 선택해서 복사하는 식으로 처리 )
    ############################################################
    drop_cols = [
        'NickName', 'IconTexture', 'ItemIcon', 'ItemTagType',
        'Weapon_R_URI', 'Weapon_L_URI', 'DropMeshURI', 'ToolTipText',
        'bTradable', 'bUnivAucTradable', 'bCashItem', 'bKeepAccountStorage',
        'bSale', 'bDestroy', 'bWorldDropExcept', 'bExtractable', 'bLockable', 
        'bCraftableAsMaterial', 'bEnhancable', 'ItemEnhanceTableID', 'bEnchantable', 
        'MaxEnhanceCount', 'SafeEnhanceCount', 'AuctionKeyWordSearchCheck', 'BuyPrice', 
        'SellPrice', 'MaxStack', 'AutoBuyMaxStack', 'ReqJob', 'ReqMinLev', 'ReqMaxLev', 
        'InventoryItemWeight', 'HuntingSpotIDs', 'CraftRecipeIDs', 'OtherSettingTableID', 
        'SetItemGroup', 'ItemOptionList', 'PassiveSkillIDs', 'RestoreLoseEquipItemByGoldCost', 
        'RestoreLoseEquipItemByGemCost', 'RestoreLostEquipItemByGemCost', 'bLosableEquipItem', 
        'bUseItemOnRiding', 'WeaponArmorIndex', 'WeaponArmorLevel', 'bRemoveOnExpired'
    ]
    df = df.drop(columns=drop_cols)
    logger.info('=== 컬럼 드랍 완료 ===')
    logger.info(df.columns.tolist())
    logger.info(df.shape)


    ############################################################
    # 결측치 확인 
    ############################################################
    logger.info('=== 결측치 확인 ===')
    logger.info(df.isnull().sum())
    logger.info('=== 고유값 확인 ===')
    logger.info(df.nunique())
    logger.info('=== 데이터 확인 ===')
    logger.info(df.head())

    ############################################################
    # 공백 제거 
    ############################################################
    str_cols = df.columns.tolist()
    for col in str_cols:
        df[col] = df[col].where(df[col].isna(), df[col].astype(str).str.strip())
    logger.info('=== 공백 제거 완료 ===')


    ############################################################
    # 컬럼 고유값 확인 
    ############################################################
    logger.info('=== 컬럼 고유값 확인 ===')
    for col in ["Type", "DetailType", "Grade"]:
        logger.info(f"{col} unique values: {df[col].dropna().unique().tolist()} \n")

    
    ############################################################
    # RowName이 Unique ID 인지 확인 
    ############################################################
    duplicate_rows = df[df.duplicated(subset=["RowName"], keep=False)]
    logger.info('=== Unique ID 확인 ===')
    logger.info(duplicate_rows)


    ############################################################
    # 이름 중복 확인 
    ############################################################
    duplicate_names = df[df.duplicated(subset=["Name"], keep=False)].sort_values("Name")
    logger.info('=== 이름 중복 확인 ===')
    logger.info(duplicate_names[["RowName", "Name", "Type", "DetailType", "Grade"]])


    ############################################################
    # 전처리 결과 저장 
    ############################################################
    output_path = "Neo4j\\data\\Item_Equipment_cleaned.csv"
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    logger.info(f"=== 전처리 결과 저장 완료: {output_path} ===")
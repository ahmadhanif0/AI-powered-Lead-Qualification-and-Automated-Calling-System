from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "user_crms" ADD IF NOT EXISTS "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
        ALTER TABLE "user_crms" ADD IF NOT EXISTS "access_token" TEXT;
        ALTER TABLE "user_crms" ADD IF NOT EXISTS "refresh_token" TEXT;
        ALTER TABLE "user_crms" ADD IF NOT EXISTS "token_expires_at" TIMESTAMPTZ;
        ALTER TABLE "user_crms" ADD IF NOT EXISTS "hubspot_portal_id" VARCHAR(100);
        ALTER TABLE "user_crms" DROP COLUMN IF EXISTS "api_secret";
        ALTER TABLE "user_crms" DROP COLUMN IF EXISTS "api_key";
        ALTER TABLE "user_crms" ALTER COLUMN "crm_type" SET DEFAULT 'hubspot';
        CREATE UNIQUE INDEX IF NOT EXISTS "uid_user_crms_user_id_3af6ab" ON "user_crms" ("user_id", "crm_type");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "uid_user_crms_user_id_3af6ab";
        ALTER TABLE "user_crms" ADD "api_secret" VARCHAR(500);
        ALTER TABLE "user_crms" ADD "api_key" VARCHAR(500) NOT NULL;
        ALTER TABLE "user_crms" DROP COLUMN "updated_at";
        ALTER TABLE "user_crms" DROP COLUMN "access_token";
        ALTER TABLE "user_crms" DROP COLUMN "refresh_token";
        ALTER TABLE "user_crms" DROP COLUMN "token_expires_at";
        ALTER TABLE "user_crms" DROP COLUMN "hubspot_portal_id";
        ALTER TABLE "user_crms" ALTER COLUMN "crm_type" DROP DEFAULT;"""


MODELS_STATE = (
    "eJztnW1v27YWx7+K4VcdkBVJ1mxD3zmpe5fNSXoT995hwyAwEm0TpUiVpJIYvfnuF6SsB+"
    "rBMW1LFlO+SygdWfpJIs/5n0Pq2zCkAcT87WcO2fD94NuQgBAO3w+09qPBEERR3iobBLjH"
    "aseYQ6ZawD0XDPhi+H4wA5jDo8EwgNxnKBKIkuH7AYkxlo3U54IhMs+bYoK+xtATdA7FQp"
    "3I3/8cDYaIBPAJ8vTf6Is3QxAH2nmiQP62avfEMlJtl0R8VDvKX7v3fIrjkOQ7R0uxoCTb"
    "GxEhW+eQQAYElIcXLJanL89udZnpFSVnmu+SnGLBJoAzEGNRuNwNGfiUSH6ICHnB34Zz+S"
    "s/np68++Xdrz/9/O7Xo8FQnUnW8stzcnn5tSeGisD1dPistgMBkj0UxpwbDAHCVXQXC8Dq"
    "2WUGJXxcsDK+FNZB+YXgycOQzMVCQjs7W0PrP6Pbi99Gt29Oz85+kNdCGfCTh/t6tek02S"
    "aR5ggjwPkjZYG3AHxhgrJiuB+kaUPONH8PrYE6izH21D8GQDUjBzODySg24pju3x1CNXwM"
    "9wbxeBOGx80Ij8sEEfeAL9BDDcZzSjEEpGGkKdqVcN5TitvimfWiW9FcQ+/85mYiTzrk/C"
    "tWDZfTEsbPV+fj2zcnii7/ipGAxaFIY8pjHkESwMAcq2baIVlTn+YgaH0G5WV7QFTBfgAC"
    "ChTCerK6ZYlrsDJ9m/7R0x6VQRDcELxcvQhrmE8vr8Z309HVJw38h9F0LLecqtZlqfXNz6"
    "WOIzvI4L+X098G8t/BXzfXY0WQcjFn6hfz/aZ/DeU5gVhQj9BHDwQFzydtTcFoNxYDLjxM"
    "54iY3ljdcg83dnW6Hd5XS+5jetlrb6Ryoz1KPEQEZJAL4z6w4QhukKnn7AOMPZ+GEYY7sK"
    "4exQ09DcAZFGzpzQDC2+MuH8M93M9SAZmtFJBMErkH/pdHwAJP21L0B0LPp2SG5rzmVqyM"
    "P/5xCzFQV1pFXdCBLm6v+jnur6Dnrfn4n6NQ7jgSCO6BxCg51tJiHMkbtpdn41Ye6kIdyW"
    "IgGIJgRxATCII+O1AvvCCcIy6ANNmJwig9jr0o1GiP6a4vxgXAeELn9nLg/gIGMYaB8n92"
    "pHGXHkxisayjkGMtPaVNo291U3gallsAAXN11vK35S+VhtaG7Mtq1F2fgPF8FraQhPk7k+"
    "ekI6Hu5z8uMdNuYiYjbaDbFm061G4X8T2PqNibfHu2iXx71izfyk16UAJ8H3LuCfoF1ggn"
    "U/jU8DyW7baC2i+hZPznVIs+UmxvrkZ//qDpJJOb63+luxcwX0xuzsv5BThjkC/M+VYMHe"
    "BawIqPB58ixCDfQtWts3cS4IElwFW36UWUCYC9uoGyuauvNbbk7dF7+5PjTbr7k+Pm/l5t"
    "q+SWfEoI9M21vrKpE/h0tCqRwJfE36IfKtu6PujAfZBLFL7SRGEcBVveWN3S3diD3tiKFK"
    "OifKOYumDxcmDdk9u3h9i6kifRGVYBfqQMojn5Ay4Vx0sixUu/LpYu1cTao18dDYYMPGYi"
    "TfHRoMQLoExqKrdzdHcx+jAePjfnltpWwrLUSoMcVky9vKCJ6RkfV55skwom710iJm8aGO"
    "UWdhaAthIOBVAAVCfc/353c13PsWBS9gGQLwb/G2DEe53aqcMnL3e9OFPWYUoDuDxAWZxB"
    "kRy+GeTc5DnVrayM3Pev07pw5LWGI85tdW7rK3dbi/UvNV5rqTym2WmtlOS0lcylsfBpCF"
    "1CtxNXVqNt4CiU7ex0a/fvKySvSQAxWHohIrGoq+hrfDAbrLsban46PvSjWuihwNOq1BYI"
    "AcNImJCsN+4QZH84ullibiqTCwlcSOBCAhcS5JXgNbFAWiHeHARkZehOr7bJyU/LcrYr5t"
    "mhiqd7kh2sAYEYF+aLQGhWVgqrrdBUtTemMDUjx/JAq+a8SobRghKjZzEzsJJhK3k9ORMZ"
    "kKXRHIHcxEqO7fSNEAQeF2Bu1jlqVo5mPl2MshqQHzEFDR5kZlGCOJMmbUUmOwhwa5h9uP"
    "l8PhkPPt2OLy7vLlfp5izuVht1yeN2PJqUAQogYqNscm7R4byfT5AEklK/u0g5h9McaMms"
    "Q6rRnqm2kKVXbMxCnKKN6yk1khGjDyioE3JewFk0tJJpKy+8ClkUny3nJxRs3fyEA89PSH"
    "PhcaImGSX3MqvuxOIe5fTUoywYIMnZmMzKrDG1pHvpel4mQF4AfcRNa1R1M0vgdtB3E/gk"
    "smSyaeddMXa9t5td5nK3bnaZu7Gbzi7L1n4yS8yXzbZyuA4woO3Z5eq+osFOZr0paOjPcl"
    "vG9Qy1b+0eyNm5alsZX7lD0hjejaeD68+TybqiED0C3XmxSFX7/e8Yxj0d0dwqcCZQ2qwY"
    "yt+/mrIh7eVsrh3SV3B0BUR9G//WFRCZFmi4r51U049LLmAo1fHQTPeqGNoCtWvZKymxCi"
    "HntRnzZsIVQ0e4nvADRT40rCIs2nSYrxxjjPa4+GMruqIaJLdKtFUtO0RLI0gA6nEmOKFj"
    "OmbpVh3ynEfix3dvT3oM9AFEyFuvwqzpAOqMrUwutJNsd2r0K1Wjne7mdLeDzyNyn5BwSl"
    "GXSlH6VYkanajwwYlmlUj7uIUTiWwSiVThuRG8gsX3NHW24lqrh34Lr7pg5xzqbFX6R4QR"
    "9Ugc3psF1RVDK5m2olTk4ZtpVF21tJJqO0/qVnWQrgTSlUC6+SoviWpfZVo7OaHeQg1ipq"
    "IMj0OfkrrgrNFzqjP9jjQDvRjfp0zOTfJiZjT7uWJo5et+ttGTebbmyVTbnCjpREknSjpR"
    "0vrFjQpFbU3LnWYlby+tdqqcCCdE2SZEJTePQcDNvP+ynS1lIB24qgka8wCgbGfxjPUWuZ"
    "q7WXueUNaz2qUeOVXpZbsZZd+ju+xSGrv7y5LIHvzlDXPPPcqzlh3mwqPRJ4dZz2TX+MyV"
    "VHez21yTYneus02uc34Dzceysq2do9mr8ksghmzpCcC/GKaXq5ZWiqPtzOSwYx20fcc/p5"
    "uEP6fN0Y/c5FTm78JtPuSEfUsdaBd1WLfMgaXQepPa6HGoZrTQgQtwNw1w+7A8RI/5rV0f"
    "4sAqwQgy5C9qp/8nW9bP/c/3cXKARXLAA2SmJXQFEzvzZ63EjPLVMKlDTHa3E2BL3xQgAt"
    "YNFs3fCi+Y7PSt8H6JUL/v62PhFT+wy4Hl+f8ZY/HR"
)

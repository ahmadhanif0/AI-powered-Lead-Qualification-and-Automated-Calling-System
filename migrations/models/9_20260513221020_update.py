from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "leads" ADD "call_sid" VARCHAR(255);
        ALTER TABLE "leads" ADD "call_provider" VARCHAR(100);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "leads" DROP COLUMN "call_sid";
        ALTER TABLE "leads" DROP COLUMN "call_provider";"""


MODELS_STATE = (
    "eJztnO9v2jgYx/+VKK86qatarmwT71jHbj1R2LXcNu10ikxigjXHTm2nLer1fz/ZIeQHIc"
    "MZP5KT34HtL9gfO48fP4/h2Q6oBzE/G0Lg2T3r2SYggHbPypWfWjYIw7RUFggwxaohhsBT"
    "JWDKBQOusHvWDGAOTy3bg9xlKBSIErtnkQhjWUhdLhgifloUEXQfQUdQH4o5ZHbP+vufU8"
    "tGxINPkCdvwx/ODEGc7ydS3VPljliEquyaiI+qofy2qeNSHAUkbRwuxJySVWtEhCz1IYEM"
    "CCg/XrBIdl/2bjnMZERxT9MmcRczGg/OQIRFZrhbMnApkfwQEXLAz7Yvv+V15+Ly7eW739"
    "5cvjuVqO2etSp5+xIPLx17LFQERhP7RdUDAeIWCmPKbR5NeUiFU8bvag5YOcC8qgCSC1YE"
    "mWA7KskAPDkYEl/MJb5ut4Lbl/7t1af+7Umn230lx0IZcONlPlpWdeI6CTeFOUOMC0e904"
    "CZV9WCuUS1Ypk0SWGmj2JraGJQA2ZOZFgmLGEAENbhuBIYhgnDcE6J1lpcCVrJ8OL8fAuG"
    "F+fnGxmqujxDlwYhIAsdihlJKznuxzZC4DlcAF/POOZUhmZCk7uUlYD8iCnY4EGuFAWIMy"
    "mp4/1sw/G8PsQKZh/Gf70fDqzPt4Or67vr8Uj2Pljwe5xWyiJ+j5FQY7wd9IdFgAKIiOss"
    "xVSxG+9xG342gY92s80jwNjRh1mQHZBoCIknme2KancbqN3NTLsbkOodb7IaYyVzJENGH5"
    "AHmTbOrLCVTPfywKvjiuITbxt5pB+AgAIFsOKok9EWqHpL8VnyopGMK5BOrm8Gd5P+zWe1"
    "I/FkR+pPBrKmk9+nlqUnbwr0Vx9ifb2efLLkW+v7eKS2tJBy4TP1jWm7yXdb9glEgjqEPj"
    "rAyw47KU6KcpPJoGALx6VRHEnaMhhVUP08KtUAd2I3UanCYyAYIHFv1ulN4NMGfCXSlpiX"
    "qqU/+DbJrfrEiJzc9L+9yq384Xj0e9I8Y3SuhuP3BcgAOR50EZfd1LDeBVlL4B7AdhP4JJ"
    "z46dU33mtiY72PbL1dBiXaGnOZV+5gImuZ8198XhgE3pjgxXIdtWRml0u+cmKj0Ks5sXml"
    "mdijTqzqvMz/zZb5v1VCcArcH4+Aec5aDe3QTW3Xq4JOUCwBBPhqViRb2ctlOrTPOeICEF"
    "GWK00rKxOmIGlmsqaty5rqZqV+KSF1DKNxgJjrggsYyLBAoOfwrwnbAvXQ/n6cVw4g56Vp"
    "gs2E14SGcDnhB4pcqHl1Iqs5YKB2gDGi6nFp7oFKbZK1IozrygOipSEkADU4BB7T0d2z8q"
    "oD8vRD8fry7KLBQB9AiJyV/6ZrAMrErYyq7CfLYI7h/59jeEOOa1cA4yH1yw5rSVXlUU0l"
    "WTD1zUmtdSc1deVFC15GcbhcTBMgFvY3tehrbG0ZndnVEqLiEWFEHRIFUz3Pdk3YSqZ7OS"
    "6kPpSua7uubCXV/azUWllYk4A1CVhzW+5nJ9v7CEYw7lBjoXoRA7JbDocuJfFPurb0nMqk"
    "tVyoI6zWHXtQDLqUyZuRTsSwjiFdE7bkcT+0LTVhAhMm2HWY4FZex/lT2uiySEGmtjJYEF"
    "/qUabehAtMuKCJ1mPnm51c8QwCrufYFnVtSTMewAuL0ej7tkVdi38Kskeu+k7Djm9qNiw3"
    "3iAXwVzVNM7fca70QYbceel9vrim+jJf2sb4ey3y9x4g0w3HZSTtdFj2EjaWj4ZOTDNu3k"
    "6Ae/pnBCJg2Q/H/rgbjzb9M8JKUtzJkCusfy2MeEOPIC+b+cnxVoeLipGhwj4kP0CGi466"
    "sbz8B702DVk="
)

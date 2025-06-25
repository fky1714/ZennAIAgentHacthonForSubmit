# エンベディングフィールド名
EMBEDDING_FIELD="embedding"

# エンベディングのディメンション数
# 使用しているエンベディングモデルに応じて変更してください
# OpenAI text-embedding-ada-002 or text-embedding-3-small: 1536
# OpenAI text-embedding-3-large: 3072
# Google Vertex AI textembedding-gecko: 768
EMBEDDING_DIMENSION=768

# (オプション) gcloudコマンドにプロジェクトIDを明示的に指定する場合
# PROJECT_ID="your-gcp-project-id" # ← 必要であれば設定してください
# GCLOUD_PROJECT_OPTION="--project=${PROJECT_ID}"
GCLOUD_PROJECT_OPTION="" # デフォルトはgcloudの現在の設定を使用

echo "Firestoreのコレクション '${COLLECTION_ID}' にベクトルインデックスを作成します。"
echo "エンベディングフィールド: '${EMBEDDING_FIELD}'"
# if [ -n "${PROJECT_ID}" ]; then
#   echo "対象プロジェクトID: '${PROJECT_ID}'"
# fi
echo "実行するgcloudコマンド:"
echo "gcloud alpha firestore indexes fields update \\"
echo "  --collection-group=${COLLECTION_ID} \\"
echo "  --field-path=${EMBEDDING_FIELD} \\"
echo "  --vector-config='{\"dimension\":${EMBEDDING_DIMENSION},\"flat\":{}}' ${GCLOUD_PROJECT_OPTION}"
echo "---------------------------------------------------------------------"
read -p "このコマンドを実行しますか？ (y/N): " confirmation

if [[ "${confirmation}" =~ ^[Yy]$ ]]; then
  echo "インデックス作成コマンドを実行します..."
  gcloud alpha firestore indexes composite create \
    --collection-group="myCollection" \
    --query-scope=COLLECTION \
    --field-config=field-path=embedding,vector-config='{"dimension":"768","flat":{}}' \
    --database="(default)"
  if [ $? -eq 0 ]; then
    echo "インデックス作成コマンドの投入に成功しました。"
    echo "インデックスの作成には時間がかかる場合があります。GCPコンソールで状況を確認してください。"
  else
    echo "インデックス作成コマンドの投入に失敗しました。"
    echo "詳細なエラーメッセージを確認してください。"
  fi
else
  echo "インデックス作成はキャンセルされました。"
fi
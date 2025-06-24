#!/bin/bash
# Firestoreのベクトルインデックスを作成するスクリプト

# 対象のコレクションID (Collection Group)
# RagChatbotAgentとprepare_rag_data.pyで設定したコレクション名に合わせてください
COLLECTION_ID="rag_chunks_all"

# エンベディングフィールド名
EMBEDDING_FIELD="embedding"

# (オプション) gcloudコマンドにプロジェクトIDを明示的に指定する場合
# PROJECT_ID="your-gcp-project-id" # ← 必要であれば設定してください
# GCLOUD_PROJECT_OPTION="--project=${PROJECT_ID}"
GCLOUD_PROJECT_OPTION="" # デフォルトはgcloudの現在の設定を使用

echo "Firestoreのコレクション '${COLLECTION_ID}' にベクトルインデックスを作成します。"
echo "エンベディングフィールド: '${EMBEDDING_FIELD}'"
# if [ -n "${PROJECT_ID}" ]; then
#   echo "対象プロジェクトID: '${PROJECT_ID}'"
# fi
echo "---------------------------------------------------------------------"
echo "実行するgcloudコマンド:"
echo "gcloud firestore indexes composite create \\"
echo "  --collection-group=${COLLECTION_ID} \\"
echo "  --field-config=vector-field=${EMBEDDING_FIELD},vector-encoding=FLAT \\"
echo "  --field-config=order=ASCENDING,field-path=metadata.original_uid \\"
echo "  --field-config=order=ASCENDING,field-path=metadata.original_doc_type ${GCLOUD_PROJECT_OPTION}"
echo "---------------------------------------------------------------------"
read -p "このコマンドを実行しますか？ (y/N): " confirmation

if [[ "${confirmation}" =~ ^[Yy]$ ]]; then
  echo "インデックス作成コマンドを実行します..."
  gcloud firestore indexes composite create \
    --collection-group=${COLLECTION_ID} \
    --field-config=vector-field=${EMBEDDING_FIELD},vector-encoding=FLAT \
    --field-config=order=ASCENDING,field-path=metadata.original_uid \
    --field-config=order=ASCENDING,field-path=metadata.original_doc_type ${GCLOUD_PROJECT_OPTION}

  if [ $? -eq 0 ]; then
    echo "インデックス作成コマンドの投入に成功しました。"
    echo "インデックスの作成には時間がかかる場合があります。GCPコンソールで状況を確認してください。"
  else
    echo "インデックス作成コマンドの投入に失敗しました。"
  fi
else
  echo "インデックス作成はキャンセルされました。"
fi

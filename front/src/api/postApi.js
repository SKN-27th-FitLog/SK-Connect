import axios from "axios";

const api = axios.create({
  // [변경 필요] 실행 환경에 맞게 수정
  // Android Emulator: http://10.0.2.2:8000
  // iOS Simulator: http://127.0.0.1:8000
  // 실기기: http://내PC아이피:8000
  baseURL: "http://127.0.0.1:8000",
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 10000,
});

const formatDate = (value) => {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${date.getFullYear()}. ${date.getMonth() + 1}. ${date.getDate()}.`;
};

const mapListPost = (item) => {
  const firstImage =
    Array.isArray(item?.image) && item.image.length > 0
      ? item.image[0]?.image_url
      : "";

  return {
    id: item?.id?.toString?.() ?? "",
    title: item?.title ?? "",
    content: item?.content ?? "",
    author: "익명", // [주석] 목록 serializer에는 작성자 없음
    authorBadge: "익",
    createdAt: formatDate(item?.created_at),
    imageUrl: firstImage || "",
    likeCount: 0, // [주석] 현재 API에 없음
    commentCount: 0, // [주석] 현재 API에 없음
    liked: false,
    category: item?.cd_table?.name ?? "",
    categoryCd: item?.post_cd ?? "",
    location: item?.map?.address_detail ?? "",
    comments: [],
  };
};

const mapDetailPost = (item) => {
  const firstImage =
    Array.isArray(item?.image) && item.image.length > 0
      ? item.image[0]?.image_url
      : "";

  return {
    id: item?.id?.toString?.() ?? "",
    title: item?.title ?? "",
    content: item?.content ?? "",
    author: item?.user?.user_id ?? "익명",
    authorBadge: (item?.user?.user_id ?? "익명")?.[0] ?? "익",
    createdAt: formatDate(item?.created_at),
    imageUrl: firstImage || "",
    likeCount: 0, // [주석] 현재 상세 API에 없음
    liked: false, // [주석] 현재 상세 API에 없음
    category: item?.category?.name ?? "",
    categoryCd: item?.post_cd ?? "",
    location: item?.map?.address_detail ?? "",
    comments: [], // [주석] 현재 상세 API에 없음
    statusCd: item?.status_cd ?? "",
  };
};

// 목록 조회: GET /posts
export const fetchPostList = async () => {
  const response = await api.get("/posts");
  const list = Array.isArray(response.data) ? response.data : [];
  return list.map(mapListPost);
};

// 상세 조회: GET /posts/:id
export const fetchPostDetail = async (postId) => {
  const response = await api.get(`/posts/${postId}`);
  return mapDetailPost(response.data);
};

// 생성: POST /api/posts
export const createPost = async ({
  title,
  content,
  selectedCategory,
  imageUrls = [],
}) => {
  const payload = {
    title: title ?? "",
    content: content ?? "",
    post_cd: selectedCategory ?? "",

    // [주석] serializer 필수값이라 임시값
    // 실제 코드값은 백엔드와 맞춰야 함
    status_cd: "STATUS_DEFAULT",
    latitude: 0,
    longitude: 0,
    address_cd: "ADDR_DEFAULT",
    address_detail: "",

    image_url: Array.isArray(imageUrls) ? imageUrls : [],
  };

  const response = await api.post("/api/posts", payload);
  return response.data;
};

export default {
  fetchPostList,
  fetchPostDetail,
  createPost,
};
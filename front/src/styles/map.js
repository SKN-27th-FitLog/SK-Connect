/**
 * 지도 관련 스타일 통합
 * - MapScreen, MapPostPreviewCard, MapPinPopup 등 지도 화면/컴포넌트에서 공통 사용
 * - 스타일 정보는 이 파일에서만 정의하고, 하위 컴포넌트는 여기서 import 해서 사용
 */
import { StyleSheet } from "react-native";
import { colors, radius, spacing } from "../theme";

const mapScreenStyles = StyleSheet.create({
  /* ---------- MapScreen ---------- */
  container: { flex: 1, backgroundColor: colors.gray[200] },
  mapArea: {
    flex: 1,
    width: "100%",
    height: "100%",
    backgroundColor: colors.gray[300],
  },
  mapPlaceholderText: {
    color: colors.gray[500],
    textAlign: "center",
    fontSize: 14,
  },
  /* WebView 카카오맵 (높이 필수) */
  mapWebViewContainer: {
    flex: 1,
    width: "100%",
    minHeight: 320,
    backgroundColor: colors.gray[300],
  },
  mapWebView: {
    flex: 1,
    width: "100%",
    minHeight: 320,
    backgroundColor: colors.gray[300],
  },
  mapWebViewFallback: {
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
  },
  /* 지도 우측 플로팅 컨트롤 (줌·내 위치) */
  mapControlsColumn: {
    position: "absolute",
    right: spacing.md,
    top: "28%",
    gap: spacing.sm,
  },
  mapControlButton: {
    width: 44,
    height: 44,
    borderRadius: radius.lg,
    backgroundColor: colors.white,
    justifyContent: "center",
    alignItems: "center",
    shadowColor: "#000",
    shadowOpacity: 0.12,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 4,
  },
  mapControlButtonDisabled: {
    opacity: 0.5,
  },
  /* 주변 게시글 목록 (마커 클릭 대체 UX) */
  pinListScroll: {
    position: "absolute",
    bottom: spacing.lg,
    left: 0,
    right: 0,
  },
  pinListContent: {
    paddingHorizontal: spacing.md,
  },
  pinListItem: {
    backgroundColor: colors.white,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderRadius: radius.lg,
    marginRight: spacing.sm,
    minWidth: 140,
    shadowColor: "#000",
    shadowOpacity: 0.1,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 3,
  },
  pinListItemSelected: {
    borderWidth: 2,
    borderColor: colors.primary,
  },
  pinListTitle: {
    fontSize: 14,
    fontWeight: "600",
    color: colors.foreground,
  },
  pinListCategory: {
    fontSize: 12,
    color: colors.gray[500],
    marginTop: 4,
  },

  /* ---------- 팝업 공통 (MapScreen 인라인 팝업 / MapPostPreviewCard) ---------- */
  popupOverlay: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: "rgba(0,0,0,0.3)",
    padding: spacing.lg,
    alignItems: "center",
  },
  popup: {
    backgroundColor: colors.white,
    borderRadius: radius.xl,
    padding: spacing.lg,
    width: "100%",
    maxWidth: 320,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 12,
    elevation: 10,
  },
  popupHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing.sm,
  },
  popupCategory: {
    fontSize: 16,
    fontWeight: "700",
    color: colors.primary,
  },
  popupClose: { color: colors.gray[400], fontSize: 18 },
  popupTitle: {
    fontSize: 17,
    fontWeight: "700",
    color: colors.foreground,
    marginBottom: 10,
  },
  popupContent: {
    fontSize: 14,
    lineHeight: 21,
    color: colors.gray[600],
    marginBottom: 12,
  },
  popupLocation: {
    fontSize: 14,
    color: colors.gray[500],
    marginBottom: 16,
  },
  popupButton: {
    height: 46,
    borderRadius: radius.lg,
    backgroundColor: colors.primary,
    justifyContent: "center",
    alignItems: "center",
  },
  popupButtonText: {
    color: colors.white,
    fontSize: 16,
    fontWeight: "700",
  },

  /* ---------- MapPostPreviewCard (게시글 미리보기 카드) ---------- */
  postPreviewCard: {
    width: 250,
    backgroundColor: colors.white,
    borderRadius: radius.xl,
    padding: spacing.lg,
    shadowColor: "#000",
    shadowOpacity: 0.15,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 4,
  },
  postPreviewHeaderRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing.md,
  },
  postPreviewCategory: {
    fontSize: 16,
    fontWeight: "700",
    color: colors.primary,
  },
  postPreviewClose: { fontSize: 18, color: colors.gray[500] },
  postPreviewTitle: {
    fontSize: 17,
    fontWeight: "700",
    color: colors.foreground,
    marginBottom: 10,
  },
  postPreviewContent: {
    fontSize: 14,
    lineHeight: 21,
    color: colors.gray[600],
    marginBottom: 12,
  },
  postPreviewLocation: {
    fontSize: 14,
    color: colors.gray[500],
    marginBottom: 16,
  },
  postPreviewButton: {
    height: 46,
    borderRadius: radius.lg,
    backgroundColor: colors.primary,
    justifyContent: "center",
    alignItems: "center",
  },
  postPreviewButtonText: {
    color: colors.white,
    fontSize: 16,
    fontWeight: "700",
  },

  /* ---------- MapPinPopup (단순 핀 팝업) ---------- */
  pinPopupContainer: {
    position: "absolute",
    left: 16,
    right: 16,
    bottom: 20,
    backgroundColor: colors.white,
    borderRadius: radius.xl,
    padding: spacing.lg,
  },
  pinPopupTitle: { fontSize: 16, fontWeight: "700", marginBottom: 6 },
  pinPopupDescription: { marginBottom: 12, fontSize: 14, color: colors.gray[600] },
  pinPopupButtonRow: { flexDirection: "row", gap: 8 },
  pinPopupButtonPrimary: {
    backgroundColor: colors.secondary,
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: radius.lg,
  },
  pinPopupButtonSecondary: {
    backgroundColor: colors.gray[200],
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: radius.lg,
  },
  pinPopupButtonText: { color: colors.white },
});

export default mapScreenStyles;

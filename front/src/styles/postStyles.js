import { StyleSheet } from "react-native";
import { ui } from "./ui";

export const postListStyles = StyleSheet.create({
    container: {
        ...ui.page,
        paddingTop: ui.verticalScale(20),
    },
 
    header: {
        ...ui.header,
        paddingTop: ui.verticalScale(20),
        paddingBottom: ui.verticalScale(10),
    },

    headerTitle: {
        ...ui.headerTitle,
        marginBottom: ui.verticalScale(12),
        fontSize: ui.scale(20),
    },

    tabs: {
        flexDirection: "row",
        gap: ui.scale(10),
        paddingBottom: ui.verticalScale(6),
        paddingTop: ui.verticalScale(3)
    },

    categoryTabsWrapper: {
        marginTop: ui.verticalScale(2),
        paddingTop: ui.verticalScale(8),
        paddingBottom: ui.verticalScale(10),
        borderTopWidth: 1,
        borderTopColor: ui.colors.gray[100],
        borderBottomWidth: 1,
        borderBottomColor: ui.colors.gray[100],
        backgroundColor: ui.colors.white,
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.03,
        shadowRadius: 4,
        elevation: 1,
    },

    categoryTabs: {
        flexDirection: "row",
        alignItems: "center",
        gap: ui.scale(10),
        paddingLeft: ui.scale(8),
        paddingRight: ui.scale(20),
    },

    tab: {
        ...ui.chip,
        height: ui.verticalScale(40),
        paddingHorizontal: ui.scale(18),
        paddingVertical: 0,
        justifyContent: "center",
        alignItems: "center",
    },

    tabActive: {
        ...ui.chipActive,
    },

    tabText: {
        ...ui.chipText,
        fontSize: ui.scale(14),
        lineHeight: ui.scale(18),
    },

    tabTextActive: {
        ...ui.chipTextActive,
    },
    tabsRow: {
    marginTop: 14,
    },

    categoryTabsWrapper: {
    backgroundColor: "#fff",
    borderTopWidth: 1,
    borderTopColor: "#f0f0f0",
    borderBottomWidth: 1,
    borderBottomColor: "#f0f0f0",
    marginBottom: 8,
    },

    list: {
        flex: 1,
        paddingHorizontal: ui.scale(ui.spacing.lg),
        paddingTop: ui.verticalScale(12),
        paddingBottom: ui.verticalScale(128),
    },

    card: {
        ...ui.card,
        marginBottom: ui.verticalScale(ui.spacing.md),
    },

    cardHeader: {
        flexDirection: "row",
        alignItems: "center",
        paddingHorizontal: ui.scale(ui.spacing.lg),
        paddingTop: ui.verticalScale(ui.spacing.md),
        paddingBottom: ui.verticalScale(ui.spacing.sm),
    },

    avatar: {
        width: ui.scale(38),
        height: ui.scale(38),
        borderRadius: ui.scale(19),
        backgroundColor: ui.colors.primary,
        alignItems: "center",
        justifyContent: "center",
    },

    avatarText: {
        color: ui.colors.white,
        fontWeight: "700",
        fontSize: ui.scale(14),
    },

    userInfo: {
        marginLeft: ui.scale(ui.spacing.sm),
    },

    userName: {
        color: ui.colors.gray[800],
        fontWeight: "600",
        fontSize: ui.scale(14),
    },

    date: {
        color: ui.colors.gray[400],
        fontSize: ui.scale(12),
        marginTop: 2,
    },

    image: {
        width: "100%",
        height: ui.verticalScale(210),
        backgroundColor: ui.colors.gray[100],
    },

    imagePlaceholder: {
        height: ui.verticalScale(136),
        backgroundColor: ui.colors.gray[50],
        marginHorizontal: ui.scale(ui.spacing.lg),
        marginBottom: ui.verticalScale(ui.spacing.sm),
        borderRadius: ui.scale(ui.radius.lg),
    },

    cardContent: {
        paddingHorizontal: ui.scale(ui.spacing.lg),
        paddingBottom: ui.verticalScale(ui.spacing.lg),
        paddingTop: 2,
    },

    title: {
        fontWeight: "800",
        fontSize: ui.scale(16),
        color: ui.colors.gray[900],
        marginBottom: 4,
    },

    content: {
        fontSize: ui.scale(14),
        color: ui.colors.gray[600],
        lineHeight: ui.scale(21),
        marginTop: 2,
    },

    actions: {
        flexDirection: "row",
        alignItems: "center",
        gap: ui.scale(ui.spacing.lg),
        marginTop: ui.verticalScale(ui.spacing.md),
    },

    actionItem: {
        flexDirection: "row",
        alignItems: "center",
        gap: 4,
    },

    heart: {
        color: ui.colors.primary,
    },

    actionText: {
        fontSize: ui.scale(13),
        color: ui.colors.gray[500],
    },

    empty: {
        paddingVertical: ui.verticalScale(72),
        alignItems: "center",
    },

    emptyText: {
        color: ui.colors.gray[400],
        fontSize: ui.scale(14),
    },

    fab: {
        ...ui.fab,
    },

    fabText: {
        ...ui.fabText,
    },
});

export const postCreateStyles = StyleSheet.create({
    safeArea: {
        ...ui.page,
    },

    container: {
        ...ui.page,
    },

    header: {
        height: ui.verticalScale(60),
        paddingHorizontal: ui.scale(14),
        flexDirection: "row",
        alignItems: "center",
        backgroundColor: ui.colors.white,
        borderBottomWidth: 1,
        borderBottomColor: "#EFEFEF",
    },

    backButton: {
        fontSize: ui.scale(34),
        color: "#374151",
        marginRight: ui.scale(10),
        lineHeight: ui.scale(34),
    },

    headerTitle: {
        fontSize: ui.scale(18),
        fontWeight: "700",
        color: ui.colors.primary,
    },

    scrollView: {
        flex: 1,
    },

    contentContainer: {
        padding: ui.scale(16),
        paddingBottom: ui.verticalScale(28),
    },
    screenTitle: {
        fontSize: ui.scale(24),
        fontWeight: "800",
        color: ui.colors.primary,
        marginBottom: ui.verticalScale(18),
    },

    section: {
        marginBottom: ui.verticalScale(22),
    },

    label: {
        fontSize: ui.scale(15),
        fontWeight: "700",
        color: "#111827",
        marginBottom: ui.verticalScale(10),
    },

    input: {
        ...ui.input,
        height: ui.verticalScale(52),
    },

    textArea: {
        height: ui.verticalScale(172),
        paddingTop: ui.verticalScale(14),
        paddingBottom: ui.verticalScale(14),
    },

    categoryGrid: {
        flexDirection: "row",
        flexWrap: "wrap",
        justifyContent: "space-between",
        rowGap: ui.verticalScale(10),
    },

    categoryButton: {
        width: "31.5%",
        height: ui.verticalScale(44),
        borderWidth: 1,
        borderColor: "#D1D5DB",
        borderRadius: ui.scale(12),
        backgroundColor: ui.colors.white,
        justifyContent: "center",
        alignItems: "center",
    },

    categoryButtonSelected: {
        backgroundColor: ui.colors.primary,
        borderColor: ui.colors.primary,
    },

    categoryButtonText: {
        fontSize: ui.scale(14),
        color: "#374151",
        fontWeight: "600",
    },

    categoryButtonTextSelected: {
        color: ui.colors.white,
        fontWeight: "700",
    },

    locationRow: {
        flexDirection: "row",
        alignItems: "center",
    },

    locationInputWrapper: {
        flex: 1,
        height: ui.verticalScale(48),
        borderWidth: 1,
        borderColor: "#D1D5DB",
        borderRadius: ui.scale(12),
        backgroundColor: ui.colors.white,
        paddingHorizontal: ui.scale(12),
        flexDirection: "row",
        alignItems: "center",
    },

    locationIcon: {
        fontSize: ui.scale(16),
        marginRight: ui.scale(8),
    },

    locationInput: {
        flex: 1,
        fontSize: ui.scale(15),
        color: "#111827",
    },

    searchButton: {
        width: ui.scale(48),
        height: ui.verticalScale(48),
        marginLeft: ui.scale(8),
        borderWidth: 1,
        borderColor: "#D1D5DB",
        borderRadius: ui.scale(12),
        backgroundColor: ui.colors.white,
        justifyContent: "center",
        alignItems: "center",
    },

    searchButtonText: {
        fontSize: ui.scale(20),
        color: "#374151",
        fontWeight: "700",
    },

    imageUploadBox: {
        width: ui.scale(132),
        height: ui.scale(132),
        borderWidth: 1,
        borderStyle: "dashed",
        borderColor: "#D1D5DB",
        borderRadius: ui.scale(14),
        backgroundColor: ui.colors.white,
        justifyContent: "center",
        alignItems: "center",
    },

    imageUploadIcon: {
        fontSize: ui.scale(28),
        marginBottom: 6,
    },

    imageUploadText: {
        fontSize: ui.scale(15),
        color: "#94A3B8",
    },

    bottomArea: {
        paddingHorizontal: ui.scale(16),
        paddingTop: ui.verticalScale(10),
        paddingBottom: ui.verticalScale(18),
        backgroundColor: ui.colors.gray[50],
    },

    submitButton: {
        ...ui.primaryButton,
    },

    submitButtonDisabled: {
        backgroundColor: "#FDBA74",
    },

    submitButtonText: {
        ...ui.primaryButtonText,
    },
    });

    export const postDetailStyles = StyleSheet.create({
    safeArea: {
        ...ui.whitePage,
    },

    container: {
        ...ui.whitePage,
    },

    contentContainer: {
        paddingBottom: ui.verticalScale(48),
    },

    header: {
        height: ui.verticalScale(60),
        paddingHorizontal: ui.scale(14),
        flexDirection: "row",
        alignItems: "center",
        backgroundColor: ui.colors.white,
        borderBottomWidth: 1,
        borderBottomColor: ui.colors.gray[100],
    },

    backButton: {
        fontSize: ui.scale(34),
        color: "#374151",
        marginRight: ui.scale(10),
        lineHeight: ui.scale(34),
    },

    headerTitle: {
        fontSize: ui.scale(18),
        fontWeight: "700",
        color: ui.colors.primary,
    },

    image: {
        width: "100%",
        height: ui.verticalScale(300),
        backgroundColor: "#E5E7EB",
    },

    section: {
        paddingHorizontal: ui.scale(20),
        paddingTop: ui.verticalScale(22),
    },

    authorRow: {
        flexDirection: "row",
        alignItems: "center",
        marginBottom: ui.verticalScale(18),
    },

    badge: {
        width: ui.scale(40),
        height: ui.scale(40),
        borderRadius: ui.scale(20),
        backgroundColor: ui.colors.primary,
        justifyContent: "center",
        alignItems: "center",
        marginRight: ui.scale(12),
    },

    badgeText: {
        color: ui.colors.white,
        fontSize: ui.scale(18),
        fontWeight: "700",
    },

    author: {
        fontSize: ui.scale(16),
        fontWeight: "600",
        color: "#111827",
    },

    date: {
        marginTop: 4,
        fontSize: ui.scale(13),
        color: "#94A3B8",
    },

    title: {
        fontSize: ui.scale(22),
        fontWeight: "800",
        color: "#0F172A",
        marginBottom: ui.verticalScale(12),
        lineHeight: ui.scale(28),
    },

    content: {
        fontSize: ui.scale(16),
        lineHeight: ui.scale(28),
        color: "#334155",
    },

    locationBox: {
        marginTop: ui.verticalScale(18),
        padding: ui.scale(14),
        borderRadius: ui.scale(14),
        backgroundColor: "#FFF7ED",
        borderWidth: 1,
        borderColor: "#FED7AA",
    },

    locationLabel: {
        fontSize: ui.scale(13),
        color: ui.colors.primary,
        fontWeight: "700",
        marginBottom: 4,
    },

    locationText: {
        fontSize: ui.scale(15),
        color: "#7C2D12",
    },

    likeRow: {
        marginTop: ui.verticalScale(24),
        paddingTop: ui.verticalScale(18),
        borderTopWidth: 1,
        borderTopColor: "#E5E7EB",
    },

    likeText: {
        fontSize: ui.scale(16),
        color: "#6B7280",
        fontWeight: "600",
    },

    commentHeader: {
        marginTop: ui.verticalScale(28),
        marginBottom: ui.verticalScale(12),
    },

    commentTitle: {
        fontSize: ui.scale(20),
        fontWeight: "700",
        color: "#0F172A",
    },

    commentInputWrapper: {
        flexDirection: "row",
        alignItems: "flex-end",
        marginBottom: ui.verticalScale(18),
        gap: ui.scale(8),
    },

    commentInput: {
        flex: 1,
        minHeight: ui.verticalScale(48),
        maxHeight: ui.verticalScale(100),
        borderWidth: 1,
        borderColor: "#D1D5DB",
        borderRadius: ui.scale(14),
        paddingHorizontal: ui.scale(14),
        paddingVertical: ui.verticalScale(12),
        fontSize: ui.scale(15),
        color: "#111827",
        backgroundColor: ui.colors.white,
    },

    commentButton: {
        minWidth: ui.scale(68),
        height: ui.verticalScale(48),
        paddingHorizontal: ui.scale(16),
        borderRadius: ui.scale(14),
        backgroundColor: ui.colors.primary,
        justifyContent: "center",
        alignItems: "center",
    },

    commentButtonText: {
        color: ui.colors.white,
        fontSize: ui.scale(15),
        fontWeight: "700",
    },

    emptyCommentText: {
        fontSize: ui.scale(14),
        color: "#94A3B8",
        marginTop: 8,
    },
    screenTitle: {
        fontSize: ui.scale(24),
        fontWeight: "800",
        color: ui.colors.primary,
        marginBottom: ui.verticalScale(18),
    },
});
#import "Headers.h"

// Background playback
%hook MLVideo
- (BOOL)playableInBackground {
    if (IS_ENABLED(BackgroundPlayback)) return YES;
    return %orig;
}
%end

%hook YTIPlayabilityStatus
- (BOOL)isPlayableInBackground {
    if (IS_ENABLED(BackgroundPlayback)) return YES;
    return %orig;
}
%end

%hook YTPlaybackData
- (BOOL)isPlayableInBackground {
    if (IS_ENABLED(BackgroundPlayback)) return YES;
    return %orig;
}
%end

%hook YTIPlayerResponse
- (BOOL)isPlayableInBackground {
    if (IS_ENABLED(BackgroundPlayback)) return YES;
    return %orig;
}
%end

%hook YTColdConfig
// Try to disable Shorts PiP
- (BOOL)shortsPlayerGlobalConfigEnableReelsPictureInPicture {
    if (IS_ENABLED(DisablesShortsPiP)) return NO;
    return %orig;
}
- (BOOL)shortsPlayerGlobalConfigEnableReelsPictureInPictureIos {
    if (IS_ENABLED(DisablesShortsPiP)) return NO;
    return %orig;
}
// Hide startup animations
- (BOOL)mainAppCoreClientIosEnableStartupAnimation {
    if (IS_ENABLED(HideStartupAni)) return NO;
    return %orig;
}
// Prevent YouTube from asking "Are you there?"
- (BOOL)enableYouthereCommandsOnIos {
    if (IS_ENABLED(BlockUpgradeDialogs)) return NO;
    return %orig;
}
// Fixes slow miniplayer
- (BOOL)enableIosFloatingMiniplayerDoubleTapToResize {
    if (IS_ENABLED(FixesSlowMiniPlayer)) return NO;
    return %orig;
}
// Use old miniplayer
- (BOOL)enableIosFloatingMiniplayer {
    if (IS_ENABLED(DisablesNewMiniPlayer)) return NO;
    return %orig;
}
%end

%hook YTHotConfig
- (BOOL)shortsPlayerGlobalConfigEnableReelsPictureInPictureAllowedFromPlayer {
    if (IS_ENABLED(DisablesShortsPiP)) return NO;
    return %orig;
}
%end

%hook YTReelModel
- (BOOL)isPiPSupported {
    if (IS_ENABLED(DisablesShortsPiP)) return NO;
    return %orig;
}
%end

%hook YTReelPlayerViewController
- (BOOL)isPictureInPictureAllowed {
    if (IS_ENABLED(DisablesShortsPiP)) return NO;
    return %orig;
}
- (void)setupPlayerForPiP {
    if (!IS_ENABLED(DisablesShortsPiP)) %orig;
}
%end

%hook YTReelWatchRootViewController
- (void)switchToPictureInPicture {
    if (!IS_ENABLED(DisablesShortsPiP)) %orig;
}
%end

// Disable Hints
%hook YTSettings
- (BOOL)areHintsDisabled {
    if (IS_ENABLED(DisableHints)) return YES;
    return %orig;
}
- (void)setHintsDisabled:(BOOL)arg1 {
    BOOL temp = IS_ENABLED(DisableHints) ? YES : arg1;
    %orig(temp);
}
%end

%hook YTSettingsImpl
- (BOOL)areHintsDisabled {
    if (IS_ENABLED(DisableHints)) return YES;
    return %orig;
}
- (void)setHintsDisabled:(BOOL)arg1 {
    BOOL temp = IS_ENABLED(DisableHints) ? YES : arg1;
    %orig(temp);
}
%end

%hook YTUserDefaults
- (BOOL)areHintsDisabled {
    if (IS_ENABLED(DisableHints)) return YES;
    return %orig;
}
- (void)setHintsDisabled:(BOOL)arg1 {
    BOOL temp = IS_ENABLED(DisableHints) ? YES : arg1;
    %orig(temp);
}
%end

// Block upgrade dialogs
%hook YTGlobalConfig
- (BOOL)shouldBlockUpgradeDialog {
    if (IS_ENABLED(BlockUpgradeDialogs)) return YES;
    return %orig;
}
- (BOOL)shouldShowUpgradeDialog {
    if (IS_ENABLED(BlockUpgradeDialogs)) return NO;
    return %orig;
}
- (BOOL)shouldShowUpgrade {
    if (IS_ENABLED(BlockUpgradeDialogs)) return NO;
    return %orig;
}
- (BOOL)shouldForceUpgrade {
    if (IS_ENABLED(BlockUpgradeDialogs)) return NO;
    return %orig;
}
%end

%hook YTYouThereController
- (BOOL)shouldShowYouTherePrompt {
    if (IS_ENABLED(HideAreYouThereDialog)) return NO;
    return %orig;
}
- (void)showYouTherePrompt {
    if (!IS_ENABLED(HideAreYouThereDialog)) %orig;
}
%end

%hook YTYouThereControllerImpl
- (BOOL)shouldShowYouTherePrompt {
    if (IS_ENABLED(HideAreYouThereDialog)) return NO;
    return %orig;
}
- (void)showYouTherePrompt {
    if (!IS_ENABLED(HideAreYouThereDialog)) %orig;
}
%end

// Disables Snackbar
%hook GOOHUDManagerInternal
- (id)sharedInstance {
    if (IS_ENABLED(DisablesSnackBar)) return nil;
    return %orig;
}
- (void)showMessageMainThread:(id)arg {
    if (!IS_ENABLED(DisablesSnackBar)) %orig;
}
- (void)activateOverlay:(id)arg {
    if (!IS_ENABLED(DisablesSnackBar)) %orig;
}
- (void)displayHUDViewForMessage:(id)arg {
    if (!IS_ENABLED(DisablesSnackBar)) %orig;
}
%end

// Remove "Play next in queue" from the menu @PoomSmart (https://github.com/qnblackcat/uYouPlus/issues/1138#issuecomment-1606415080)
%hook YTMenuItemVisibilityHandler
- (BOOL)shouldShowServiceItemRenderer:(YTIMenuConditionalServiceItemRenderer *)renderer {
    int iconnum = renderer.icon.iconType;
    if (iconnum == 251 && IS_ENABLED(RemovePlayInNextQueueOption)) {
        return NO;
    }
    if (iconnum == 895 && IS_ENABLED(RemoveAddToLastQueueOption)) {
        return NO;
    }
    return %orig;
}
%end

%hook YTMenuItemVisibilityHandlerImpl
- (BOOL)shouldShowServiceItemRenderer:(YTIMenuConditionalServiceItemRenderer *)renderer {
    int iconnum = renderer.icon.iconType;
    if (iconnum == 251 && IS_ENABLED(RemovePlayInNextQueueOption)) {
        return NO;
    }
    if (iconnum == 895 && IS_ENABLED(RemoveAddToLastQueueOption)) {
        return NO;
    }
    return %orig;
}
%end

// Remove flyout menu options
%hook YTDefaultSheetController
- (void)addAction:(YTActionSheetAction *)action {
    UIButton *button = action.button;
    NSString *iden = button.accessibilityIdentifier;
    NSString *imageName = [button.currentImage description];

    // Method 1: Filter from accessibilityIdentifier
    NSDictionary *actionsToRemove = @{
        @"7": @(IS_ENABLED(RemoveDownloadOption)),
        @"1": @(IS_ENABLED(RemoveWatchLaterOption)),
        @"3": @(IS_ENABLED(RemoveSaveOption)),
        @"4": @(IS_ENABLED(RemoveRemoveFromPlaylistOption)),
        @"5": @(IS_ENABLED(RemoveShareOption)),
        @"6": @(IS_ENABLED(RemoveShareOption)),
        @"12": @(IS_ENABLED(RemoveNotInterestedOption)),
        @"22": @(IS_ENABLED(RemoveInfoOption)),
        @"36": @(IS_ENABLED(RemoveFilterOption)),
        @"40": @(IS_ENABLED(RemoveNotifyOption)),
        @"58": @(IS_ENABLED(RemoveReportOption))
    };
    if ([actionsToRemove[iden] boolValue]) return;

    // Method 2: Filter from imageName
    NSDictionary *imageNameToRemove = @{
        @"youtube_music": @(IS_ENABLED(RemoveYouTubeMusicOption)),
        @"flag": @(IS_ENABLED(RemoveReportOption)),
        @"alert_bubble": @(IS_ENABLED(RemoveFeedBackOption)),
        @"bookmark": @(IS_ENABLED(RemoveSaveOption)),
        @"circle_slash": @(IS_ENABLED(RemoveNotInterestedOption)),
        @"x_circle": @(IS_ENABLED(RemoveDontRecommendOption)),
        @"chromecast": @(IS_ENABLED(RemoveCastOption)),
        @"shuffle": @(IS_ENABLED(RemoveShuffleOption)),
        @"person_x": @(IS_ENABLED(RemoveUnSubOption)),
        @"help_circle": @(IS_ENABLED(RemoveHelpOption)),
        @"eye_slash": @(IS_ENABLED(RemoveHideFromPlaylistOption)),
        @"player_full_enter_alt": @(IS_ENABLED(RemoveClearScreenOption)),
        @"info_circle": @(IS_ENABLED(RemoveInfoOption))
    };
    for (NSString *key in imageNameToRemove) {
        if ([imageName containsString:key]) {
            if ([imageNameToRemove[key] boolValue]) {
                return;
            }
            break;
        }
    }
    %orig;
}
%end

// YTSlientVote (https://github.com/PoomSmart/YTSilentVote)
%hook YTInnerTubeResponseWrapper
- (id)initWithResponse:(id)response cacheContext:(id)arg2 requestStatistics:(id)arg3 mutableSharedData:(id)arg4 {
    if (!IS_ENABLED(HideLikeDislikeVotes)) return %orig;
    if ([response isKindOfClass:%c(YTILikeResponse)]
        || [response isKindOfClass:%c(YTIDislikeResponse)]
        || [response isKindOfClass:%c(YTIRemoveLikeResponse)]) return nil;
    return %orig;
}
%end

%hook NSParagraphStyle
+ (NSWritingDirection)defaultWritingDirectionForLanguage:(id)lang {
    if (IS_ENABLED(DisablesRTL)) return NSWritingDirectionLeftToRight;
    return %orig;
}
+ (NSWritingDirection)_defaultWritingDirection {
    if (IS_ENABLED(DisablesRTL)) return NSWritingDirectionLeftToRight;
    return %orig;
}
%end

%hook UIDevice
- (UIUserInterfaceIdiom)userInterfaceIdiom {
    if (INTFORVAL(DeviceUIIndex) == 1) {
        return UIUserInterfaceIdiomPad;
    }
    if (INTFORVAL(DeviceUIIndex) == 2) {
        return UIUserInterfaceIdiomPhone;
    }
    return %orig;
}
%end

%hook UIKeyboardImpl
+ (BOOL)isFloating {
    if (IS_ENABLED(FloatingKeyboard) && isPad()) return YES;
    return %orig;
}
%end

%hook YTEngagementPanelHeaderView
- (void)setSubheader:(UIView *)view {
    if (!IS_ENABLED(HideEngagementSubbar)) %orig;
}
%end

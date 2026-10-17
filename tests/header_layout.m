#define main GBOSViewerMain
#import "../host/viewer.m"
#undef main

@interface HeaderTestApp : App
@property(nonatomic) NSInteger selectedMode;
@property(nonatomic) BOOL settingsInvoked;
@end
@implementation HeaderTestApp
- (void)choosePointerMode:(NSMenuItem *)sender { self.selectedMode=sender.tag; }
- (void)showSettings:(id)sender { self.settingsInvoked=YES; }
@end

int main(int argc, char **argv) { @autoreleasepool {
 [NSApplication sharedApplication];
 [NSApp setActivationPolicy:NSApplicationActivationPolicyAccessory];
 HeaderTestApp *app=[HeaderTestApp new];
 app.ctlFd=-1;
 app.window=[[NSWindow alloc] initWithContentRect:NSMakeRect(0,0,900,400)
  styleMask:NSWindowStyleMaskTitled|NSWindowStyleMaskClosable|NSWindowStyleMaskMiniaturizable|NSWindowStyleMaskResizable
  backing:NSBackingStoreBuffered defer:NO];
 app.window.toolbar=[[NSToolbar alloc] initWithIdentifier:@"legacy-header-test"];
 app.window.toolbar.displayMode=NSToolbarDisplayModeIconOnly;
 app.window.toolbarStyle=NSWindowToolbarStyleUnified;
 app.window.subtitle=@"Captured mouse: click to capture, Control-Option releases";
 [app.window orderBack:nil];
 [app.window displayIfNeeded];
 CGFloat before=app.window.frame.size.height-app.window.contentLayoutRect.size.height;
 [app configureHeader];
 [app.window displayIfNeeded];
 CGFloat after=app.window.frame.size.height-app.window.contentLayoutRect.size.height;
 NSCAssert(after<before && after<=32, @"Header must be one compact row: %.1f -> %.1f",before,after);
 NSCAssert(app.window.subtitle.length==0,@"No subtitle row");
 NSStackView *actions=(NSStackView *)app.window.titlebarAccessoryViewControllers[0].view;
 NSCAssert(actions.arrangedSubviews.count==4,@"Four header actions");
 for(NSView *control in actions.arrangedSubviews) {
  if(control==app.headerPointer) {
   NSMenu *menu=app.headerPointer.menu;
   NSCAssert(menu.numberOfItems==4,@"All pointer modes remain available");
   NSMenuItem *captured=menu.itemArray[1];
   NSCAssert([NSApp sendAction:captured.action to:captured.target from:captured],@"Pointer menu action");
   NSCAssert(app.selectedMode==2,@"Captured mode target");
  }
  if([control.identifier isEqualToString:@"Settings"]) {
   NSButton *button=(NSButton *)control;
   NSCAssert([NSApp sendAction:button.action to:button.target from:button],@"Settings action");
   NSCAssert(app.settingsInvoked,@"Settings target");
  }
 }
 NSCAssert(!app.headerRestart.enabled,@"No restart without an owned VM");
 [app updatePointerHint];
 NSCAssert(app.window.subtitle.length==0,@"Pointer hints cannot restore a subtitle row");
 [app.window setContentSize:NSMakeSize(560,350)];
 [app.window displayIfNeeded];
 NSCAssert(app.window.frame.size.height-app.window.contentLayoutRect.size.height<=32,@"Compact when narrow");
 if(argc>1) {
  [app.window setContentSize:NSMakeSize(900,400)];
  [app.window displayIfNeeded];
  NSView *frame=app.window.contentView.superview;
  NSBitmapImageRep *image=[frame bitmapImageRepForCachingDisplayInRect:frame.bounds];
  [frame cacheDisplayInRect:frame.bounds toBitmapImageRep:image];
  NSData *png=[image representationUsingType:NSBitmapImageFileTypePNG properties:@{}];
  NSCAssert([png writeToFile:@(argv[1]) atomically:YES],@"Save header fixture screenshot");
 }
 printf("PASS: header %.0f -> %.0f pt; menu targets, settings, restart guard, hints and narrow window\n",before,after);
 [app.window orderOut:nil];
 return 0;
}}

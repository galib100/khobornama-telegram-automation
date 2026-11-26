import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:path_provider/path_provider.dart';
import 'dart:io';
import '../models/news_models.dart';
import '../utils/constants.dart';
import 'loading_skeleton.dart';
import 'entrance_fader.dart';

class ShareableNewsCard extends StatefulWidget {
  final NewsArticle news;

  const ShareableNewsCard({super.key, required this.news});

  @override
  State<ShareableNewsCard> createState() => _ShareableNewsCardState();
}

class _ShareableNewsCardState extends State<ShareableNewsCard> {
  final GlobalKey _cardKey = GlobalKey();
  late final PageController _cardPageController;
  int _selectedDesignIndex = 0;
  bool _isProcessing = false;

  @override
  void initState() {
    super.initState();
    _cardPageController = PageController();
  }

  @override
  void dispose() {
    _cardPageController.dispose();
    super.dispose();
  }

  Future<Uint8List?> _captureCard() async {
    try {
      final boundary = _cardKey.currentContext?.findRenderObject() as RenderRepaintBoundary?;
      if (boundary == null) return null;
      final ui.Image image = await boundary.toImage(pixelRatio: 3.0);
      final ByteData? byteData = await image.toByteData(format: ui.ImageByteFormat.png);
      return byteData?.buffer.asUint8List();
    } catch (e) {
      debugPrint('Error capturing card image: $e');
      return null;
    }
  }

  Future<void> _shareCardImage() async {
    if (_isProcessing) return;
    setState(() => _isProcessing = true);

    try {
      final pngBytes = await _captureCard();
      if (pngBytes == null) throw Exception('Image capture failed');

      final tempDir = await getTemporaryDirectory();
      final file = File('${tempDir.path}/khobornama_card_${DateTime.now().millisecondsSinceEpoch}.png');
      await file.writeAsBytes(pngBytes);

      final shareText = '${widget.news.title}\n\nhttps://play.google.com/store/apps/details?id=info.bd.khobornama&pcampaignid=web_share\n\nখবরনামা অ্যাপ থেকে পড়ুন';
      await SharePlus.instance.share(ShareParams(files: [XFile(file.path)], text: shareText));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('শেয়ার করতে সমস্যা হয়েছে: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _isProcessing = false);
    }
  }

  Future<void> _saveImageToDevice() async {
    if (_isProcessing) return;
    setState(() => _isProcessing = true);

    try {
      final pngBytes = await _captureCard();
      if (pngBytes == null) throw Exception('Image capture failed');

      final tempDir = await getTemporaryDirectory();
      final file = File('${tempDir.path}/khobornama_card_${DateTime.now().millisecondsSinceEpoch}.png');
      await file.writeAsBytes(pngBytes);

      final shareText = '${widget.news.title}\n\nhttps://play.google.com/store/apps/details?id=info.bd.khobornama&pcampaignid=web_share\n\nখবরনামা অ্যাপ ডাউনলোড করুন';
      await SharePlus.instance.share(ShareParams(files: [XFile(file.path)], text: shareText));

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('ছবি সফলভাবে প্রস্তুত হয়েছে!'),
            backgroundColor: AppConstants.colorSuccess,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('সংরক্ষণ করতে সমস্যা হয়েছে: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _isProcessing = false);
    }
  }

  void _copyLink() {
    const link = 'https://play.google.com/store/apps/details?id=info.bd.khobornama&pcampaignid=web_share';
    Clipboard.setData(const ClipboardData(text: link));
    Navigator.of(context).pop();
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('প্লে-স্টোর অ্যাপ লিঙ্ক কপি করা হয়েছে!'),
        backgroundColor: AppConstants.colorSuccess,
      ),
    );
  }

  void _shareViaText() {
    final text = '${widget.news.title}\n\nhttps://play.google.com/store/apps/details?id=info.bd.khobornama&pcampaignid=web_share\n\nখবরনামা অ্যাপ থেকে পড়ুন';
    SharePlus.instance.share(ShareParams(text: text));
  }

  Future<void> _shareToWhatsApp() async {
    final text = '${widget.news.title}\n\nhttps://play.google.com/store/apps/details?id=info.bd.khobornama&pcampaignid=web_share\n\nখবরনামা অ্যাপ থেকে পড়ুন';
    final whatsappUri = Uri.parse('whatsapp://send?text=${Uri.encodeComponent(text)}');
    final webUri = Uri.parse('https://api.whatsapp.com/send?text=${Uri.encodeComponent(text)}');

    try {
      if (await canLaunchUrl(whatsappUri)) {
        await launchUrl(whatsappUri, mode: LaunchMode.externalApplication);
      } else if (await canLaunchUrl(webUri)) {
        await launchUrl(webUri, mode: LaunchMode.externalApplication);
      } else {
        _shareViaText();
      }
    } catch (_) {
      _shareViaText();
    }
  }

  Future<void> _shareToFacebook() async {
    const newsUrl = 'https://play.google.com/store/apps/details?id=info.bd.khobornama&pcampaignid=web_share';
    final fbAppUri = Uri.parse('fb://facewebmodal/f?href=${Uri.encodeComponent(newsUrl)}');
    final fbWebUri = Uri.parse('https://www.facebook.com/sharer/sharer.php?u=${Uri.encodeComponent(newsUrl)}');

    try {
      if (await canLaunchUrl(fbAppUri)) {
        await launchUrl(fbAppUri, mode: LaunchMode.externalApplication);
      } else if (await canLaunchUrl(fbWebUri)) {
        await launchUrl(fbWebUri, mode: LaunchMode.externalApplication);
      } else {
        _shareViaText();
      }
    } catch (_) {
      _shareViaText();
    }
  }

  Future<void> _shareToMessenger() async {
    const newsUrl = 'https://play.google.com/store/apps/details?id=info.bd.khobornama&pcampaignid=web_share';
    final messengerUri = Uri.parse('fb-messenger://share?link=${Uri.encodeComponent(newsUrl)}');

    try {
      if (await canLaunchUrl(messengerUri)) {
        await launchUrl(messengerUri, mode: LaunchMode.externalApplication);
      } else {
        _shareViaText();
      }
    } catch (_) {
      _shareViaText();
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Container(
      decoration: BoxDecoration(
        color: isDark ? AppConstants.bgPrimaryDark : Colors.white,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
      ),
      padding: EdgeInsets.only(
        top: 12,
        left: 16,
        right: 16,
        bottom: MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: EntranceFader(
        child: SingleChildScrollView(
          child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Drag handle
            Center(
              child: Container(
                width: 44,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.grey.shade300,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 8),

            // Header Row
            Row(
              children: [
                IconButton(
                  icon: const Icon(Icons.close_rounded, size: 24),
                  onPressed: () => Navigator.of(context).pop(),
                ),
                const SizedBox(width: 4),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'ফটো কার্ড শেয়ার করুন',
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                          fontSize: 17,
                        ),
                      ),
                      const Text(
                        'সোয়াইপ করে পছন্দমতো ফটো কার্ড ডিজাইন বেছে নিন',
                        style: TextStyle(fontSize: 11, color: AppConstants.textSecondary),
                      ),
                    ],
                  ),
                ),
              ],
            ),

            const SizedBox(height: 12),

            // PageView Carousel of 5 Card Designs
            SizedBox(
              height: 380,
              child: PageView.builder(
                controller: _cardPageController,
                itemCount: 5,
                onPageChanged: (index) {
                  setState(() {
                    _selectedDesignIndex = index;
                  });
                },
                itemBuilder: (context, index) {
                  final isCurrent = index == _selectedDesignIndex;
                  return Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 4),
                    child: RepaintBoundary(
                      key: isCurrent ? _cardKey : null,
                      child: _buildCardDesign(index),
                    ),
                  );
                },
              ),
            ),

            const SizedBox(height: 10),

            // Design Controller Indicator Row (Previous, Dots, Next, Design Label)
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                IconButton(
                  icon: const Icon(Icons.chevron_left_rounded, size: 28),
                  onPressed: _selectedDesignIndex > 0
                      ? () {
                          _cardPageController.previousPage(
                            duration: const Duration(milliseconds: 300),
                            curve: Curves.easeInOut,
                          );
                        }
                      : null,
                ),

                // Indicator Dots
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: List.generate(5, (index) {
                    final isSelected = index == _selectedDesignIndex;
                    return AnimatedContainer(
                      duration: const Duration(milliseconds: 250),
                      margin: const EdgeInsets.symmetric(horizontal: 3),
                      width: isSelected ? 18 : 6,
                      height: 6,
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(3),
                        color: isSelected ? AppConstants.primaryColor : Colors.grey.shade300,
                      ),
                    );
                  }),
                ),

                IconButton(
                  icon: const Icon(Icons.chevron_right_rounded, size: 28),
                  onPressed: _selectedDesignIndex < 4
                      ? () {
                          _cardPageController.nextPage(
                            duration: const Duration(milliseconds: 300),
                            curve: Curves.easeInOut,
                          );
                        }
                      : null,
                ),
              ],
            ),

            const SizedBox(height: 16),

            // Share Platforms Row (WhatsApp, Facebook, Messenger, Copy Link, More)
            Text(
              'শেয়ার করুন',
              style: theme.textTheme.bodySmall?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),

            Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildSocialIcon(
                  label: 'WhatsApp',
                  icon: FontAwesomeIcons.whatsapp,
                  color: const Color(0xFF25D366),
                  onTap: _shareToWhatsApp,
                ),
                _buildSocialIcon(
                  label: 'Facebook',
                  icon: FontAwesomeIcons.facebook,
                  color: const Color(0xFF1877F2),
                  onTap: _shareToFacebook,
                ),
                _buildSocialIcon(
                  label: 'Messenger',
                  icon: FontAwesomeIcons.facebookMessenger,
                  color: const Color(0xFF00B2FF),
                  onTap: _shareToMessenger,
                ),
                _buildSocialIcon(
                  label: 'লিঙ্ক কপি',
                  icon: Icons.link_rounded,
                  color: Colors.grey.shade700,
                  onTap: _copyLink,
                ),
                _buildSocialIcon(
                  label: 'আরও',
                  icon: Icons.more_horiz_rounded,
                  color: Colors.grey.shade600,
                  onTap: _shareCardImage,
                ),
              ],
            ),

            const SizedBox(height: 16),

            // Bottom Action Buttons
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _isProcessing ? null : _saveImageToDevice,
                    icon: const Icon(Icons.download_rounded, size: 18),
                    label: const Text(
                      'ছবি হিসেবে সংরক্ষণ',
                      style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                    ),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 13),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(AppConstants.radiusMedium),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _isProcessing ? null : _shareCardImage,
                    icon: _isProcessing
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                          )
                        : const Icon(Icons.share_rounded, size: 18),
                    label: const Text(
                      'শেয়ার করুন',
                      style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                    ),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppConstants.primaryColor,
                      padding: const EdgeInsets.symmetric(vertical: 13),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(AppConstants.radiusMedium),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    ),
  );
}

  // Master Switcher for Card Designs
  Widget _buildCardDesign(int index) {
    switch (index) {
      case 0:
        return _buildDesign1Jamuna();
      case 1:
        return _buildDesign2Somoy();
      case 2:
        return _buildDesign3Kalbela();
      case 3:
        return _buildDesign4ProthomAlo();
      case 4:
        return _buildDesign5DarkTrendy();
      default:
        return _buildDesign1Jamuna();
    }
  }

  // Helper Badge for News Provider Logo
  Widget _buildSourceLogoBadge({double height = 20, bool lightBg = true}) {
    final source = widget.news.source;
    final bool hasLogo = source.logo != null && source.logo!.trim().isNotEmpty;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      constraints: BoxConstraints(maxHeight: height + 10, maxWidth: 120),
      decoration: BoxDecoration(
        color: lightBg ? Colors.white : Colors.white12,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(
          color: lightBg ? Colors.grey.shade300 : Colors.white24,
          width: 0.8,
        ),
        boxShadow: lightBg
            ? [BoxShadow(color: Colors.black.withAlpha(20), blurRadius: 4, offset: const Offset(0, 2))]
            : null,
      ),
      child: hasLogo
          ? CachedNetworkImage(
              imageUrl: source.logo!,
              height: height,
              fit: BoxFit.contain,
              placeholder: (_, _) => Text(
                source.name,
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.bold,
                  color: lightBg ? const Color(0xFF0F172A) : Colors.white,
                ),
              ),
              errorWidget: (_, _, _) => Text(
                source.name,
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.bold,
                  color: lightBg ? const Color(0xFF0F172A) : Colors.white,
                ),
              ),
            )
          : Text(
              source.name,
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.bold,
                color: lightBg ? const Color(0xFF0F172A) : Colors.white,
              ),
            ),
    );
  }

  // --- DESIGN 1: Jamuna TV Style (Bold Red Bottom Banner & Footer) ---
  Widget _buildDesign1Jamuna() {
    final bool hasImage = widget.news.image != null && widget.news.image!.isNotEmpty;

    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF8B0000),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withAlpha(20),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        children: [
          // Top Image (Larger Height)
          Expanded(
            flex: 7,
            child: hasImage
                ? CachedNetworkImage(
                    imageUrl: widget.news.image!,
                    width: double.infinity,
                    fit: BoxFit.cover,
                    placeholder: (_, _) => const ShimmerImageBox(),
                    errorWidget: (_, _, _) => Container(color: Colors.grey.shade900),
                  )
                : Container(color: Colors.grey.shade900),
          ),

          // Red Title Box (Compact Vertical Spacing)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.fromLTRB(14, 8, 14, 8),
            color: const Color(0xFF990000),
            child: Column(
              children: [
                Text(
                  widget.news.title,
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    height: 1.3,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'প্রকাশিত: ${widget.news.publishedAt.split('T').first}',
                  style: const TextStyle(
                    color: Color(0xFFFFD700),
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),

          // Footer Strip with Khobornama Logo + Website + Source Logo Badge
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            color: const Color(0xFF660000),
            child: Row(
              children: [
                Image.asset('assets/logo.png', height: 18, width: 18),
                const SizedBox(width: 5),
                const Text(
                  'খবরনামা',
                  style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 11),
                ),
                const SizedBox(width: 6),
                const Text(
                  '• khobornama.info.bd',
                  style: TextStyle(color: Color(0xFFFFD700), fontSize: 10, fontWeight: FontWeight.w600),
                ),
                const Spacer(),
                _buildSourceLogoBadge(height: 14, lightBg: true),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // --- DESIGN 2: Somoy News Style (Gradient Fade + Red Key Headline + Dual Logos) ---
  Widget _buildDesign2Somoy() {
    final bool hasImage = widget.news.image != null && widget.news.image!.isNotEmpty;

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.grey.shade200),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withAlpha(15),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        children: [
          // Image with Gradient Fade into White (Larger Height)
          Expanded(
            flex: 7,
            child: Stack(
              children: [
                if (hasImage)
                  CachedNetworkImage(
                    imageUrl: widget.news.image!,
                    width: double.infinity,
                    height: double.infinity,
                    fit: BoxFit.cover,
                    placeholder: (_, _) => const ShimmerImageBox(),
                    errorWidget: (_, _, _) => Container(color: Colors.grey.shade200),
                  )
                else
                  Container(color: Colors.grey.shade200),
                Positioned.fill(
                  child: Container(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [
                          Colors.transparent,
                          Colors.white.withAlpha(100),
                          Colors.white,
                        ],
                        stops: const [0.3, 0.7, 1.0],
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),

          // Headline & Dual Logos (Compact Padding)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
            child: Column(
              children: [
                Text(
                  widget.news.title,
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Color(0xFFE11B2D),
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    height: 1.3,
                  ),
                ),
                const SizedBox(height: 8),

                // Logos Row: Khobornama + Source Logo
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Image.asset('assets/logo.png', height: 18, width: 18),
                        const SizedBox(width: 5),
                        const Text(
                          'খবরনামা',
                          style: TextStyle(
                            color: Color(0xFF0F172A),
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(width: 10),
                    _buildSourceLogoBadge(height: 16, lightBg: true),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  '${widget.news.publishedAt.split('T').first}  •  khobornama.info.bd',
                  style: const TextStyle(fontSize: 10, color: Color(0xFF64748B), fontWeight: FontWeight.w600),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // --- DESIGN 3: Kalbela Style (Floating Source Logo & Name + Date Badge + Bottom Red Bar) ---
  Widget _buildDesign3Kalbela() {
    final bool hasImage = widget.news.image != null && widget.news.image!.isNotEmpty;
    final sourceName = widget.news.source.name;

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.grey.shade300),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withAlpha(15),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        children: [
          // Top Image Section with Header Overlay
          Expanded(
            flex: 7,
            child: Stack(
              children: [
                if (hasImage)
                  CachedNetworkImage(
                    imageUrl: widget.news.image!,
                    width: double.infinity,
                    height: double.infinity,
                    fit: BoxFit.cover,
                    placeholder: (_, _) => const ShimmerImageBox(),
                    errorWidget: (_, _, _) => Container(color: Colors.grey.shade200),
                  )
                else
                  Container(color: Colors.grey.shade200),

                // Top Header Overlay: Khobornama Logo (Left) + News Source Logo & Name Badge (Right)
                Positioned(
                  top: 10,
                  left: 10,
                  right: 10,
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      // Khobornama Brand Badge (No fill color)
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Image.asset('assets/logo.png', height: 22, width: 22),
                          const SizedBox(width: 5),
                          const Text(
                            'খবরনামা',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 13,
                              fontWeight: FontWeight.bold,
                              shadows: [
                                Shadow(
                                  blurRadius: 4,
                                  color: Colors.black87,
                                  offset: Offset(0, 1),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),

                      // News Source Logo Badge
                      _buildSourceLogoBadge(height: 20, lightBg: true),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // Date & Source Pill Bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 3),
            margin: const EdgeInsets.only(top: 6),
            decoration: BoxDecoration(
              color: const Color(0xFF800000),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              '${widget.news.publishedAt.split('T').first}${sourceName.isNotEmpty ? '  •  $sourceName' : ''}',
              style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
            ),
          ),

          // Bottom Headline (Compact Vertical Spacing)
          Expanded(
            flex: 3,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
              child: Center(
                child: Text(
                  widget.news.title,
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Color(0xFFCC0000),
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    height: 1.3,
                  ),
                ),
              ),
            ),
          ),

          // Dark Red Bottom Strip
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 5),
            color: const Color(0xFF800000),
            child: const Text(
              '« « « khobornama.info.bd • সব খবর এক জায়গায় » » »',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
            ),
          ),
        ],
      ),
    );
  }

  // --- DESIGN 4: Prothom Alo Style (Split Image + Source Logo Badge + Off-white Bottom) ---
  Widget _buildDesign4ProthomAlo() {
    final bool hasImage = widget.news.image != null && widget.news.image!.isNotEmpty;

    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFFF1F5F9),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.grey.shade300),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withAlpha(15),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        children: [
          // Top Image (Larger Height)
          Expanded(
            flex: 7,
            child: Stack(
              clipBehavior: Clip.none,
              children: [
                if (hasImage)
                  CachedNetworkImage(
                    imageUrl: widget.news.image!,
                    width: double.infinity,
                    height: double.infinity,
                    fit: BoxFit.cover,
                    placeholder: (_, _) => const ShimmerImageBox(),
                    errorWidget: (_, _, _) => Container(color: Colors.grey.shade300),
                  )
                else
                  Container(color: Colors.grey.shade300),

                // Floating Source Logo Badge at Bottom Center of Image
                Positioned(
                  bottom: -14,
                  left: 0,
                  right: 0,
                  child: Center(
                    child: _buildSourceLogoBadge(height: 20, lightBg: true),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Title (Compact Padding)
          Expanded(
            flex: 3,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 2),
              child: Center(
                child: Text(
                  widget.news.title,
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Color(0xFFB30000),
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    height: 1.3,
                  ),
                ),
              ),
            ),
          ),

          // Minimal Footer (Khobornama + Date + Domain)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            color: Colors.white,
            child: Row(
              children: [
                Image.asset('assets/logo.png', height: 16, width: 16),
                const SizedBox(width: 4),
                const Text(
                  'খবরনামা',
                  style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
                ),
                const Spacer(),
                Text(
                  '${widget.news.publishedAt.split('T').first} | khobornama.info.bd',
                  style: const TextStyle(fontSize: 10, color: Color(0xFF64748B), fontWeight: FontWeight.w500),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // --- DESIGN 5: Dark Modern Social Card (CableGram Style) ---
  Widget _buildDesign5DarkTrendy() {
    final bool hasImage = widget.news.image != null && widget.news.image!.isNotEmpty;

    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withAlpha(30),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Top Header: Khobornama Logo + News Source Logo Badge
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Image.asset('assets/logo.png', height: 20, width: 20),
                  const SizedBox(width: 6),
                  const Text(
                    'khobornama',
                    style: TextStyle(color: Color(0xFFFACC15), fontWeight: FontWeight.bold, fontSize: 14),
                  ),
                ],
              ),
              _buildSourceLogoBadge(height: 16, lightBg: true),
            ],
          ),
          const SizedBox(height: 6),

          // Bold Yellow/White Title (Compact Padding)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
            child: Text(
              widget.news.title,
              textAlign: TextAlign.center,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: Color(0xFFFACC15),
                fontSize: 15,
                fontWeight: FontWeight.bold,
                height: 1.3,
              ),
            ),
          ),
          const SizedBox(height: 6),

          // Image Container at Bottom (Significantly Larger Image: flex 7)
          Expanded(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(10),
              child: Container(
                width: double.infinity,
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.white24, width: 1),
                ),
                child: hasImage
                    ? CachedNetworkImage(
                        imageUrl: widget.news.image!,
                        fit: BoxFit.cover,
                        placeholder: (_, _) => const ShimmerImageBox(),
                        errorWidget: (_, _, _) => Container(color: Colors.white10),
                      )
                    : Container(color: Colors.white10),
              ),
            ),
          ),
          const SizedBox(height: 6),

          // Footer Row with Website Domain
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                widget.news.publishedAt.split('T').first,
                style: const TextStyle(fontSize: 10, color: Colors.white54, fontWeight: FontWeight.w500),
              ),
              const Text(
                'khobornama.info.bd',
                style: TextStyle(fontSize: 10, color: Color(0xFFFACC15), fontWeight: FontWeight.bold),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSocialIcon({
    required String label,
    required dynamic icon,
    required Color color,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: color.withAlpha(25),
            ),
            child: Center(
              child: icon is FaIconData
                  ? FaIcon(icon, color: color, size: 20)
                  : Icon(icon as IconData, color: color, size: 22),
            ),
          ),
          const SizedBox(height: 6),
          Text(
            label,
            style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w500),
          ),
        ],
      ),
    );
  }
}

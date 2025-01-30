import time

def example_function():
    import cv2
    import numpy as np
    import random

    # Charger l'image
    image_path = "mur1.jpg"  # Remplacez par le chemin de votre image
    image = cv2.imread(image_path)

    # Vérifier si l'image a été correctement chargée
    if image is None:
        print("Erreur : Impossible de charger l'image. Vérifiez le chemin.")
        exit()

    # Convertir l'image en niveaux de gris
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Appliquer CLAHE pour améliorer le contraste
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray_image = clahe.apply(gray_image)

    # Créer un détecteur de QR code
    qr_detector = cv2.QRCodeDetector()

    # Détecter et décoder le QR code
    data, points, _ = qr_detector.detectAndDecode(image)

    if points is not None:
        # Convertir les points en entiers
        points = points[0].astype(int)

        # Extraire les coordonnées des coins du QR code
        top_left, top_right, bottom_right, bottom_left = points

        # Tracer un rectangle autour du QR code
        cv2.polylines(image, [points], isClosed=True, color=(0, 255, 0), thickness=2)

        # Définir l'origine du repère comme le coin inférieur gauche du QR code
        origin = tuple(bottom_left)

        # Tracer les axes du plan orthonormé
        cv2.arrowedLine(image, origin, (origin[0] + 100, origin[1]), (255, 0, 0), 2, tipLength=0.2)  # Axe X (rouge)
        cv2.arrowedLine(image, origin, (origin[0], origin[1] - 100), (0, 0, 255), 2, tipLength=0.2)  # Axe Y (bleu)

        # Calculer la conversion pixel -> cm (QR code = 13 cm dans la vraie vie)
        qr_width_px = np.linalg.norm(top_right - top_left)
        pixel_to_cm = 13 / qr_width_px
        print(f"Conversion pixel -> cm : {pixel_to_cm:.4f} cm/px")

        # Appliquer un flou pour réduire le bruit
        blurred_image = cv2.GaussianBlur(gray_image, (5, 5), 0)

        # Appliquer un seuillage global pour détecter les défauts sombres
        threshold_value = int(np.mean(gray_image) * 0.4)
        _, binary_image = cv2.threshold(blurred_image, threshold_value, 255, cv2.THRESH_BINARY_INV)

        # Trouver les contours
        contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Copier l'image originale pour dessiner les contours fusionnés
        output_image = image.copy()

        # Convertir les points du QR code en float32 pour compatibilité avec pointPolygonTest
        qr_contour = np.array(points, dtype=np.float32)

        # Fonction pour calculer la largeur maximale réelle d'une fissure
        def calculate_max_width(contour):
            max_width = 0
            for i in range(len(contour)):
                for j in range(i + 1, len(contour)):
                    # Calculer la distance entre deux points du contour
                    distance = cv2.norm(contour[i][0] - contour[j][0])
                    max_width = max(max_width, distance)
            return max_width

        # Traiter chaque défaut détecté
        min_contour_area = 500  # Seuil pour ignorer les petits contours
        defect_count = 0  # Compteur de défauts valides
        for i, contour in enumerate(contours):
            if cv2.contourArea(contour) > min_contour_area:
                # Vérifier si le défaut est dans la zone du QR code en testant plusieurs points du contour
                inside_qr = False
                for point in contour:
                    px, py = map(float, point[0])  # Assurez-vous que px et py sont de type float
                    if cv2.pointPolygonTest(qr_contour, (px, py), False) >= 0:
                        inside_qr = True
                        break
                
                if inside_qr:
                    continue  # Ignorer ce défaut

                # Calculer la boîte englobante
                x, y, w, h = cv2.boundingRect(contour)

                # Incrémenter le compteur de défauts valides
                defect_count += 1

                # Calculer les dimensions et la position
                defect_position_px = (x, y)
                defect_position_cm = ((x - origin[0]) * pixel_to_cm, (origin[1] - y) * pixel_to_cm)
                max_width_px = calculate_max_width(contour)
                width_cm = max_width_px * pixel_to_cm
                height_cm = h * pixel_to_cm

                # Colorier l'intérieur du défaut
                color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                cv2.drawContours(output_image, [contour], -1, color, thickness=cv2.FILLED)

                # Annoter l'image avec les informations
                info_text = f"Defaut {defect_count}: {width_cm:.2f}x{height_cm:.2f} cm"
                cv2.putText(output_image, info_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        #         # Afficher les informations dans la console avec conversion explicite des nombres numpy
        #         print(f"Defaut {defect_count}:")
        #         print(f"  - Position (px): {defect_position_px}")
        #         print(f"  - Position (cm): ({defect_position_cm[0]:.2f}, {defect_position_cm[1]:.2f})")
        #         print(f"  - Dimensions (cm): {width_cm:.2f} x {height_cm:.2f}")


        # # Afficher le nombre total de défauts détectés
        # print(f"Nombre total de défauts détectés: {defect_count}")

    else:
        print("Aucun QR Code détecté.")
        exit()

    # # Enregistrer ou afficher l'image
    # output_path = "output_with_colored_defects.jpg"
    # cv2.imwrite(output_path, output_image)
    # print(f"Image annotée enregistrée sous : {output_path}")

    # # Affichage (optionnel)
    # cv2.imshow("Image avec repere et defauts", output_image)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()


                    
                    
def measure_execution_time(func, iterations=10):
    start_time = time.time()  # Commence à mesurer le temps
    for _ in range(iterations):
        func()  # Appelle la fonction
    end_time = time.time()  # Arrête de mesurer le temps
    
    total_time = end_time - start_time
    average_time = total_time / iterations
    
    print(f"Temps total pour {iterations} itérations : {total_time:.5f} secondes")
    print(f"Temps moyen par itération : {average_time:.5f} secondes")

# Appeler la fonction de mesure
measure_execution_time(example_function, 10)

